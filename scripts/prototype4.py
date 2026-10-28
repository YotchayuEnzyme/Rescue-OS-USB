#!/usr/bin/env python3
"""Rescue-OS GUI Prototype v0.4 — English-only UI/UX prototype.

Safety scope:
- Reads block-device metadata through lsblk only.
- Does not mount, unmount, repair, format, scan, eject, copy, or write to disks.
- The recovery wizard is a UI workflow preview, not a recovery implementation.
- Selecting a destination only opens a folder chooser; no files are created.
- Read-only status and source/destination separation are NOT verified by this prototype.

Requirements on Alpine Linux:
    apk add python3 py3-gobject3 gtk+3.0 util-linux
    python3 ~/Desktop/rescue_gui_v0_4.py
"""

import json
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

APP_NAME = "Rescue-OS"
APP_VERSION = "Prototype v0.4"


# ---------- Formatting helpers ----------
def escape_markup(value):
    """Escape values before inserting them into GTK Pango markup."""
    text = str(value)
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("'", "&apos;")
                .replace('"', "&quot;"))


def format_bytes(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unknown size"
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    for unit in units:
        if number < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(number)} {unit}"
            return f"{number:.1f} {unit}"
        number /= 1024.0
    return f"{number:.1f} PiB"


def read_block_devices():
    """Read devices with lsblk. This function never performs disk writes."""
    if not shutil.which("lsblk"):
        return {"ok": False, "error": "The 'lsblk' command was not found. Install util-linux and try again."}

    command = [
        "lsblk", "--json", "--bytes", "--tree", "--output",
        "NAME,PATH,TYPE,SIZE,FSTYPE,LABEL,MODEL,TRAN,RM,RO,MOUNTPOINT"
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=8
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"lsblk exited with code {result.returncode}"
            return {"ok": False, "error": detail}
        data = json.loads(result.stdout)
        disks = [item for item in data.get("blockdevices", []) if item.get("type") == "disk"]
        return {"ok": True, "disks": disks}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Reading device metadata timed out. Try refreshing again."}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


class RescueOSWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=f"{APP_NAME} — {APP_VERSION}")
        self.set_default_size(600, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(0)
        self.connect("destroy", Gtk.main_quit)

        self.current_page = "Dashboard"
        self.nav_buttons = {}
        self.disk_cache = []
        self.disk_load_state = "idle"
        self.disk_load_generation = 0
        self.disk_error = ""
        self.disk_data_by_row = {}
        self.selected_disk = None
        self.destination_path = ""
        self.recovery_step = 0
        self.results_preview = False

        self.disk_list_box = None
        self.disk_count_label = None
        self.disk_detail_box = None
        self.recovery_body = None
        self.recovery_step_buttons = []
        self.recovery_continue_button = None

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)
        root.pack_start(self.build_sidebar(), False, False, 0)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_min_content_width(560)
        root.pack_start(self.scroller, True, True, 0)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_border_width(28)
        self.scroller.add(self.content)

        self.apply_css()
        self.show_page("Dashboard")

    # ---------- Shared widgets ----------
    def build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(224, -1)
        sidebar.set_border_width(18)
        sidebar.get_style_context().add_class("sidebar")

        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        brand_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.DIALOG)
        brand.pack_start(brand_icon, False, False, 0)
        brand_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name = Gtk.Label()
        name.set_markup('<span size="large" weight="bold">Rescue-OS</span>')
        name.set_xalign(0)
        sub = Gtk.Label(label="Recovery environment")
        sub.set_xalign(0)
        sub.get_style_context().add_class("sidebar-muted")
        brand_text.pack_start(name, False, False, 0)
        brand_text.pack_start(sub, False, False, 0)
        brand.pack_start(brand_text, True, True, 0)
        brand.set_margin_bottom(28)
        sidebar.pack_start(brand, False, False, 0)

        nav_items = [
            ("Dashboard", "Dashboard", "Overview", "view-grid-symbolic"),
            ("Recovery", "Recover Files", "Find a source device", "folder-saved-search-symbolic"),
            ("DriveHealth", "Drive Health", "Health diagnostics", "utilities-system-monitor-symbolic"),
            ("Tools", "System Tools", "Additional utilities", "applications-system-symbolic"),
            ("About", "About", "About this prototype", "help-about-symbolic"),
        ]
        for page_id, label, tooltip, icon_name in nav_items:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_halign(Gtk.Align.FILL)
            button.set_tooltip_text(tooltip)
            button.get_style_context().add_class("nav-button")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            row.pack_start(image, False, False, 0)
            row.pack_start(text, True, True, 0)
            button.add(row)
            button.connect("clicked", self.on_navigation_clicked, page_id)
            sidebar.pack_start(button, False, False, 0)
            self.nav_buttons[page_id] = button

        spacer = Gtk.Box()
        sidebar.pack_start(spacer, True, True, 0)

        safety_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        safety_card.set_border_width(12)
        safety_card.get_style_context().add_class("sidebar-note")
        safety_heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        safety_icon = Gtk.Image.new_from_icon_name("security-high-symbolic", Gtk.IconSize.BUTTON)
        safety_title = Gtk.Label(label="Prototype mode")
        safety_title.set_xalign(0)
        safety_title.get_style_context().add_class("sidebar-note-title")
        safety_heading.pack_start(safety_icon, False, False, 0)
        safety_heading.pack_start(safety_title, True, True, 0)
        safety_card.pack_start(safety_heading, False, False, 0)
        safety_body = Gtk.Label(label="Device details only. No disk changes or file recovery.")
        safety_body.set_xalign(0)
        safety_body.set_line_wrap(True)
        safety_body.get_style_context().add_class("sidebar-muted")
        safety_card.pack_start(safety_body, False, False, 0)
        sidebar.pack_start(safety_card, False, False, 0)

        version = Gtk.Label(label=APP_VERSION)
        version.set_xalign(0)
        version.get_style_context().add_class("sidebar-muted")
        version.set_margin_top(10)
        sidebar.pack_start(version, False, False, 0)
        return sidebar

    def clear_content(self):
        for child in self.content.get_children():
            self.content.remove(child)

    def clear_box(self, box):
        for child in box.get_children():
            box.remove(child)

    def page_heading(self, eyebrow, title, subtitle):
        eyebrow_label = Gtk.Label(label=eyebrow.upper())
        eyebrow_label.set_xalign(0)
        eyebrow_label.get_style_context().add_class("eyebrow")
        self.content.pack_start(eyebrow_label, False, False, 0)

        title_label = Gtk.Label()
        title_label.set_markup(f'<span size="xx-large" weight="bold">{escape_markup(title)}</span>')
        title_label.set_xalign(0)
        title_label.set_line_wrap(True)
        self.content.pack_start(title_label, False, False, 0)

        subtitle_label = Gtk.Label(label=subtitle)
        subtitle_label.set_xalign(0)
        subtitle_label.set_line_wrap(True)
        subtitle_label.set_max_width_chars(100)
        subtitle_label.get_style_context().add_class("muted")
        self.content.pack_start(subtitle_label, False, False, 0)

    def make_card(self, title, body, status=None, icon_name=None, style_class="card"):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        card.set_border_width(16)
        card.get_style_context().add_class(style_class)

        if icon_name:
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            top.pack_start(icon, False, False, 0)
            title_label = Gtk.Label()
            title_label.set_markup(f'<span weight="bold">{escape_markup(title)}</span>')
            title_label.set_xalign(0)
            top.pack_start(title_label, True, True, 0)
            card.pack_start(top, False, False, 0)
        else:
            title_label = Gtk.Label()
            title_label.set_markup(f'<span weight="bold">{escape_markup(title)}</span>')
            title_label.set_xalign(0)
            card.pack_start(title_label, False, False, 0)

        body_label = Gtk.Label(label=body)
        body_label.set_xalign(0)
        body_label.set_line_wrap(True)
        body_label.set_max_width_chars(70)
        card.pack_start(body_label, False, False, 0)

        if status:
            status_label = Gtk.Label(label=status)
            status_label.set_xalign(0)
            status_label.get_style_context().add_class("status-neutral")
            card.pack_start(status_label, False, False, 0)
        return card

    def add_section_title(self, title, subtitle=None):
        label = Gtk.Label()
        label.set_markup(f'<span size="large" weight="bold">{escape_markup(title)}</span>')
        label.set_xalign(0)
        self.content.pack_start(label, False, False, 0)
        if subtitle:
            desc = Gtk.Label(label=subtitle)
            desc.set_xalign(0)
            desc.set_line_wrap(True)
            desc.get_style_context().add_class("muted")
            self.content.pack_start(desc, False, False, 0)

    def add_button(self, label, callback, primary=False, icon_name=None):
        button = Gtk.Button(label=label)
        if primary:
            button.get_style_context().add_class("suggested-action")
        if icon_name:
            image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
            button.set_image(image)
            button.set_always_show_image(True)
        button.connect("clicked", callback)
        return button

    def set_active_nav(self, page_id):
        for key, button in self.nav_buttons.items():
            context = button.get_style_context()
            if key == page_id:
                context.add_class("active")
            else:
                context.remove_class("active")

    # ---------- Navigation ----------
    def on_navigation_clicked(self, _button, page_id):
        self.show_page(page_id)

    def show_page(self, page_id):
        self.current_page = page_id
        self.set_active_nav(page_id)
        self.clear_content()
        self.disk_list_box = None
        self.disk_count_label = None
        self.disk_detail_box = None
        self.recovery_body = None
        self.recovery_continue_button = None
        self.recovery_step_buttons = []

        if page_id == "Dashboard":
            self.show_dashboard()
        elif page_id == "Recovery":
            self.show_recovery()
        elif page_id == "DriveHealth":
            self.show_drive_health()
        elif page_id == "Tools":
            self.show_tools()
        else:
            self.show_about()
        self.content.show_all()

    # ---------- Dashboard ----------
    def show_dashboard(self):
        self.page_heading(
            "Recovery workspace", "Dashboard",
            "A clear starting point for checking devices and planning a safe file-recovery workflow."
        )

        quick_cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        quick_cards.pack_start(self.make_card(
            "System environment", "Alpine Linux with the XFCE desktop.",
            "Environment overview", "computer-symbolic"
        ), True, True, 0)
        quick_cards.pack_start(self.make_card(
            "Storage discovery", "Read device metadata using lsblk.",
            "Read-only discovery", "drive-harddisk-symbolic"
        ), True, True, 0)
        quick_cards.pack_start(self.make_card(
            "Data protection", "Recovery actions stay disabled until safety checks exist.",
            "No writes from this prototype", "security-high-symbolic"
        ), True, True, 0)
        self.content.pack_start(quick_cards, False, False, 0)

        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        hero.set_border_width(22)
        hero.get_style_context().add_class("hero-card")
        hero_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero_label = Gtk.Label(label="RECOVER FILES")
        hero_label.set_xalign(0)
        hero_label.get_style_context().add_class("eyebrow")
        hero_left.pack_start(hero_label, False, False, 0)
        hero_title = Gtk.Label()
        hero_title.set_markup('<span size="x-large" weight="bold">Find a source device</span>')
        hero_title.set_xalign(0)
        hero_left.pack_start(hero_title, False, False, 0)
        hero_desc = Gtk.Label(label="Review detected disks, choose a destination folder, and inspect the safety review workflow. File recovery itself is not enabled yet.")
        hero_desc.set_xalign(0)
        hero_desc.set_line_wrap(True)
        hero_left.pack_start(hero_desc, False, False, 0)
        hero.pack_start(hero_left, True, True, 0)
        hero_button = self.add_button("Open Recovery", lambda _b: self.show_page("Recovery"), True, "go-next-symbolic")
        hero_button.set_valign(Gtk.Align.CENTER)
        hero.pack_start(hero_button, False, False, 0)
        self.content.pack_start(hero, False, False, 0)

        self.add_section_title("Before you begin")
        checklist = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        checklist.pack_start(self.make_check_row(
            "Identify the correct source", "Compare device path, size, model, and partitions.", "document-properties-symbolic"
        ), False, False, 0)
        checklist.pack_start(self.make_check_row(
            "Choose a separate destination", "The destination must not be the source disk.", "folder-symbolic"
        ), False, False, 0)
        checklist.pack_start(self.make_check_row(
            "Verify protection before recovery", "A UI label alone cannot prove that a filesystem is mounted read-only.", "security-high-symbolic"
        ), False, False, 0)
        self.content.pack_start(checklist, False, False, 0)

    def make_check_row(self, title, body, icon_name):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_border_width(12)
        row.get_style_context().add_class("subtle-row")
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        row.pack_start(icon, False, False, 0)
        body_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        heading = Gtk.Label()
        heading.set_markup(f'<span weight="bold">{escape_markup(title)}</span>')
        heading.set_xalign(0)
        desc = Gtk.Label(label=body)
        desc.set_xalign(0)
        desc.set_line_wrap(True)
        desc.get_style_context().add_class("muted")
        body_box.pack_start(heading, False, False, 0)
        body_box.pack_start(desc, False, False, 0)
        row.pack_start(body_box, True, True, 0)
        return row

    # ---------- Recovery wizard ----------
    def show_recovery(self):
        self.page_heading(
            "Guided workflow", "Recover Files",
            "Review the workflow step by step. This prototype can discover devices, but it cannot recover files yet."
        )
        self.build_stepper()
        self.recovery_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.content.pack_start(self.recovery_body, True, True, 0)
        self.render_recovery_step()

    def build_stepper(self):
        stepper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        step_specs = [
            (0, "1", "Source"),
            (1, "2", "Destination"),
            (2, "3", "Safety review"),
            (3, "4", "Results"),
        ]
        self.recovery_step_buttons = []
        for index, number, label in step_specs:
            item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            item.set_border_width(9)
            item.get_style_context().add_class("step-item")
            badge = Gtk.Label(label=number)
            badge.set_size_request(28, 28)
            badge.set_justify(Gtk.Justification.CENTER)
            badge.get_style_context().add_class("step-number")
            item.pack_start(badge, False, False, 0)
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            text.get_style_context().add_class("step-label")
            item.pack_start(text, True, True, 0)
            if index == self.recovery_step:
                item.get_style_context().add_class("step-current")
            elif index < self.recovery_step:
                item.get_style_context().add_class("step-done")
            stepper.pack_start(item, True, True, 0)
            self.recovery_step_buttons.append(item)
        self.content.pack_start(stepper, False, False, 0)

    def rerender_recovery(self):
        if self.current_page != "Recovery":
            return
        self.show_page("Recovery")

    def render_recovery_step(self):
        self.clear_box(self.recovery_body)
        if self.recovery_step == 0:
            self.render_source_step()
        elif self.recovery_step == 1:
            self.render_destination_step()
        elif self.recovery_step == 2:
            self.render_safety_step()
        else:
            self.render_results_step()
        self.recovery_body.show_all()

    def render_source_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Select a source device",
            "Choose the disk that contains the files you want to recover. Device names and sizes come from lsblk; virtual machines may show virtual disks rather than the host computer's physical drives.",
            "Detected devices are not mounted by this screen.", "drive-harddisk-symbolic"
        ), False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        refresh = self.add_button("Refresh devices", self.on_refresh_disks, False, "view-refresh-symbolic")
        toolbar.pack_start(refresh, False, False, 0)
        self.disk_count_label = Gtk.Label(label="Reading device information…")
        self.disk_count_label.set_xalign(0)
        self.disk_count_label.get_style_context().add_class("muted")
        toolbar.pack_start(self.disk_count_label, True, True, 0)
        self.recovery_body.pack_start(toolbar, False, False, 0)

        self.disk_list_box = Gtk.ListBox()
        self.disk_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.disk_list_box.get_style_context().add_class("disk-list")
        self.disk_list_box.connect("row-selected", self.on_disk_selected)
        self.recovery_body.pack_start(self.disk_list_box, False, False, 0)

        self.disk_detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.recovery_body.pack_start(self.disk_detail_box, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.pack_start(Gtk.Box(), True, True, 0)
        self.recovery_continue_button = self.add_button("Continue to destination", self.on_continue_to_destination, True, "go-next-symbolic")
        self.recovery_continue_button.set_sensitive(self.selected_disk is not None)
        nav.pack_start(self.recovery_continue_button, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

        self.render_disk_rows()
        if self.disk_load_state == "idle":
            self.load_real_disks_async()
        elif self.disk_load_state == "loading":
            self.disk_count_label.set_text("Reading device information…")
        elif self.disk_load_state == "loaded":
            self.disk_count_label.set_text(f"Detected disk devices: {len(self.disk_cache)}")
        elif self.disk_load_state == "error":
            self.disk_count_label.set_text("Could not read device information.")
            err = Gtk.Label(label=self.disk_error or "Unknown error")
            err.set_xalign(0)
            err.set_line_wrap(True)
            err.get_style_context().add_class("error-text")
            self.disk_list_box.add(err)
            self.disk_list_box.show_all()

    def render_disk_rows(self):
        if self.disk_list_box is None:
            return
        self.clear_box(self.disk_list_box)
        self.disk_data_by_row = {}
        if self.disk_load_state == "error":
            return
        selected_path = None
        if self.selected_disk:
            selected_path = self.selected_disk.get("path") or ("/dev/" + str(self.selected_disk.get("name", "unknown")))
        selected_row = None
        for disk in self.disk_cache:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("disk-row")
            self.disk_data_by_row[row] = disk
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_border_width(13)
            icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.DIALOG)
            box.pack_start(icon, False, False, 0)

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            title_value = disk.get("model") or disk.get("label") or disk.get("name") or "Unknown device"
            title = Gtk.Label()
            title.set_markup(f'<span weight="bold">{escape_markup(title_value)}</span>')
            title.set_xalign(0)
            details.pack_start(title, False, False, 0)

            path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
            transport = (disk.get("tran") or "Connection not reported").upper()
            partition_count = len(disk.get("children") or [])
            detail_text = f"{path}  ·  {transport}  ·  {partition_count} partition(s) reported"
            sub = Gtk.Label(label=detail_text)
            sub.set_xalign(0)
            sub.set_line_wrap(True)
            sub.get_style_context().add_class("muted")
            details.pack_start(sub, False, False, 0)
            box.pack_start(details, True, True, 0)

            size = Gtk.Label(label=format_bytes(disk.get("size")))
            size.get_style_context().add_class("size-badge")
            size.set_valign(Gtk.Align.CENTER)
            box.pack_start(size, False, False, 0)
            row.add(box)
            self.disk_list_box.add(row)
            if selected_path and path == selected_path:
                selected_row = row

        if self.disk_load_state == "loaded" and not self.disk_cache:
            empty = Gtk.Label(label="No disk devices were detected by lsblk.")
            empty.set_xalign(0)
            empty.set_line_wrap(True)
            empty.set_margin_top(8)
            empty.set_margin_bottom(8)
            empty.get_style_context().add_class("muted")
            self.disk_list_box.add(empty)
        self.disk_list_box.show_all()
        if selected_row is not None:
            self.disk_list_box.select_row(selected_row)

    def on_disk_selected(self, _list_box, row):
        if row is None:
            self.selected_disk = None
            if self.disk_detail_box:
                self.clear_box(self.disk_detail_box)
            if self.recovery_continue_button:
                self.recovery_continue_button.set_sensitive(False)
            return
        disk = self.disk_data_by_row.get(row)
        if not disk:
            return
        self.selected_disk = disk
        if self.recovery_continue_button:
            self.recovery_continue_button.set_sensitive(True)
        if self.disk_detail_box is None:
            return
        self.clear_box(self.disk_detail_box)

        device_path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
        model = disk.get("model") or "Not reported"
        transport = disk.get("tran") or "Not reported"
        removable = "Yes" if disk.get("rm") in (1, "1", True) else "No / not reported"
        ro = disk.get("ro")
        if ro in (1, "1", True):
            ro_text = "Yes — block-device flag only"
        elif ro in (0, "0", False):
            ro_text = "No — block-device flag only"
        else:
            ro_text = "Not reported"
        summary = self.make_card(
            "Selected source", f"Device: {device_path}\nSize: {format_bytes(disk.get('size'))}\nModel: {model}\nConnection: {transport}\nRemovable: {removable}\nKernel block-device RO flag: {ro_text}",
            "Filesystem read-only status has not been verified.", "drive-harddisk-symbolic"
        )
        self.disk_detail_box.pack_start(summary, False, False, 0)

        partition_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        partition_title = Gtk.Label()
        partition_title.set_markup('<span weight="bold">Partitions reported by the system</span>')
        partition_title.set_xalign(0)
        partition_frame.pack_start(partition_title, False, False, 0)
        partitions = disk.get("children") or []
        if not partitions:
            msg = Gtk.Label(label="No partitions were reported for this device.")
            msg.set_xalign(0)
            msg.get_style_context().add_class("muted")
            partition_frame.pack_start(msg, False, False, 0)
        else:
            for part in partitions:
                part_path = part.get("path") or ("/dev/" + str(part.get("name", "unknown")))
                fs = part.get("fstype") or "Unknown filesystem"
                label = part.get("label") or "No label"
                mount = part.get("mountpoint") or "Not mounted / not reported"
                line = f"{part_path}  ·  {format_bytes(part.get('size'))}\nFilesystem: {fs}  ·  Label: {label}\nMount point: {mount}"
                partition_frame.pack_start(self.make_card(part.get("name") or part_path, line), False, False, 0)
        self.disk_detail_box.pack_start(partition_frame, False, False, 0)
        note = Gtk.Label(label="Safety note: the RO flag describes the block device only. It does not prove the filesystem is mounted read-only.")
        note.set_xalign(0)
        note.set_line_wrap(True)
        note.get_style_context().add_class("warning-text")
        self.disk_detail_box.pack_start(note, False, False, 0)
        self.disk_detail_box.show_all()

    def on_refresh_disks(self, _button):
        self.load_real_disks_async()

    def load_real_disks_async(self):
        if self.current_page != "Recovery":
            return
        self.disk_load_generation += 1
        generation = self.disk_load_generation
        self.disk_load_state = "loading"
        if self.disk_count_label:
            self.disk_count_label.set_text("Reading device information…")
        if self.disk_list_box:
            self.clear_box(self.disk_list_box)
            loading = Gtk.Label(label="Scanning visible block devices…")
            loading.set_xalign(0)
            loading.set_margin_top(8)
            loading.get_style_context().add_class("muted")
            self.disk_list_box.add(loading)
            self.disk_list_box.show_all()

        def worker():
            result = read_block_devices()
            GLib.idle_add(self.finish_disk_load, generation, result)

        threading.Thread(target=worker, daemon=True).start()

    def finish_disk_load(self, generation, result):
        if generation != self.disk_load_generation:
            return GLib.SOURCE_REMOVE

        # Always update cached state, even if the user navigated away while lsblk ran.
        if not result.get("ok"):
            self.disk_load_state = "error"
            self.disk_cache = []
            self.disk_error = result.get("error", "Unknown error")
        else:
            self.disk_load_state = "loaded"
            self.disk_error = ""
            self.disk_cache = result.get("disks", [])

        if self.current_page != "Recovery" or self.disk_list_box is None:
            return GLib.SOURCE_REMOVE

        if self.disk_load_state == "error":
            self.disk_count_label.set_text("Could not read device information.")
            self.clear_box(self.disk_list_box)
            err = Gtk.Label(label=self.disk_error)
            err.set_xalign(0)
            err.set_line_wrap(True)
            err.get_style_context().add_class("error-text")
            self.disk_list_box.add(err)
            self.disk_list_box.show_all()
            self.content.show_all()
            return GLib.SOURCE_REMOVE

        self.disk_count_label.set_text(f"Detected disk devices: {len(self.disk_cache)}")
        # Keep a selection only if the same device path still exists after refresh.
        old_path = None
        if self.selected_disk:
            old_path = self.selected_disk.get("path") or ("/dev/" + str(self.selected_disk.get("name", "unknown")))
        self.selected_disk = None
        self.render_disk_rows()
        if old_path:
            for row, disk in self.disk_data_by_row.items():
                path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
                if path == old_path:
                    self.disk_list_box.select_row(row)
                    break
        self.content.show_all()
        return GLib.SOURCE_REMOVE

    def on_continue_to_destination(self, _button):
        if self.selected_disk is None:
            return
        self.recovery_step = 1
        self.rerender_recovery()

    def render_destination_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Choose a destination folder",
            "Recovered files should be saved to a separate destination, never back onto the source device. In this prototype, selecting a folder does not create or copy any files.",
            "Destination separation is not verified automatically yet.", "folder-symbolic"
        ), False, False, 0)

        selected_path = self.selected_disk.get("path", "Unknown device") if self.selected_disk else "No source selected"
        source_card = self.make_card("Selected source", selected_path, "Source selection carried forward")
        self.recovery_body.pack_start(source_card, False, False, 0)

        dest_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dest_box.set_border_width(16)
        dest_box.get_style_context().add_class("card")
        label = Gtk.Label()
        label.set_markup('<span weight="bold">Destination folder</span>')
        label.set_xalign(0)
        dest_box.pack_start(label, False, False, 0)

        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.destination_label = Gtk.Label(label=self.destination_path or "No destination selected")
        self.destination_label.set_xalign(0)
        self.destination_label.set_line_wrap(True)
        self.destination_label.get_style_context().add_class("muted")
        path_row.pack_start(self.destination_label, True, True, 0)
        choose = self.add_button("Choose folder…", self.on_choose_destination, False, "folder-open-symbolic")
        path_row.pack_start(choose, False, False, 0)
        dest_box.pack_start(path_row, False, False, 0)
        self.recovery_body.pack_start(dest_box, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        back = self.add_button("Back", lambda _b: self.change_recovery_step(0), False, "go-previous-symbolic")
        nav.pack_start(back, False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        next_button = self.add_button("Continue to safety review", lambda _b: self.change_recovery_step(2), True, "go-next-symbolic")
        next_button.set_sensitive(bool(self.destination_path))
        nav.pack_start(next_button, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def on_choose_destination(self, _button):
        dialog = Gtk.FileChooserDialog(
            title="Choose destination folder", parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                           "Select Folder", Gtk.ResponseType.ACCEPT)
        dialog.set_modal(True)
        if self.destination_path:
            try:
                dialog.set_current_folder(self.destination_path)
            except Exception:
                pass
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            if path:
                self.destination_path = path
        dialog.destroy()
        self.rerender_recovery()

    def render_safety_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Safety review",
            "Review the information below before any future recovery operation. The prototype deliberately blocks real recovery because it cannot yet prove the required safety conditions.",
            "Recovery is not available in this build", "security-high-symbolic"
        ), False, False, 0)

        source = self.selected_disk.get("path", "Unknown") if self.selected_disk else "No source selected"
        self.recovery_body.pack_start(self.make_review_row("Source device selected", source, "review-pending"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Destination folder selected", self.destination_path or "Not selected", "review-pending"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Source filesystem verified read-only", "NOT VERIFIED — backend check not implemented", "review-warning"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Destination confirmed separate from source", "NOT VERIFIED — device relationship check not implemented", "review-warning"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Filesystem safety checks", "NOT VERIFIED — no mount or filesystem operations are run", "review-warning"), False, False, 0)

        warning = Gtk.Label(label="Do not treat this review as permission to recover files. No recovery command is connected to this interface.")
        warning.set_xalign(0)
        warning.set_line_wrap(True)
        warning.get_style_context().add_class("warning-text")
        self.recovery_body.pack_start(warning, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.pack_start(self.add_button("Back", lambda _b: self.change_recovery_step(1), False, "go-previous-symbolic"), False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        disabled = Gtk.Button(label="Start recovery (unavailable)")
        disabled.set_sensitive(False)
        disabled.set_tooltip_text("Real recovery is disabled until backend safety checks are implemented.")
        nav.pack_start(disabled, False, False, 0)
        preview = self.add_button("Preview results screen", lambda _b: self.show_result_preview(), False, "go-next-symbolic")
        nav.pack_start(preview, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def make_review_row(self, title, detail, style_class):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_border_width(13)
        row.get_style_context().add_class("review-row")
        status = Gtk.Label(label="!" if style_class == "review-warning" else "•")
        status.set_size_request(28, 28)
        status.get_style_context().add_class("review-icon")
        row.pack_start(status, False, False, 0)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        heading = Gtk.Label()
        heading.set_markup(f'<span weight="bold">{escape_markup(title)}</span>')
        heading.set_xalign(0)
        desc = Gtk.Label(label=detail)
        desc.set_xalign(0)
        desc.set_line_wrap(True)
        desc.get_style_context().add_class("muted")
        labels.pack_start(heading, False, False, 0)
        labels.pack_start(desc, False, False, 0)
        row.pack_start(labels, True, True, 0)
        row.get_style_context().add_class(style_class)
        return row

    def show_result_preview(self):
        self.results_preview = True
        self.recovery_step = 3
        self.rerender_recovery()

    def render_results_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Recovery results preview",
            "This is a preview of the results page only. No files have been recovered, copied, scanned, or changed.",
            "PREVIEW ONLY — no operation was started", "document-properties-symbolic"
        ), False, False, 0)

        summary = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        summary.set_border_width(18)
        summary.get_style_context().add_class("card")
        title = Gtk.Label()
        title.set_markup('<span weight="bold">Session summary</span>')
        title.set_xalign(0)
        summary.pack_start(title, False, False, 0)
        src = self.selected_disk.get("path", "No source selected") if self.selected_disk else "No source selected"
        for label in [
            f"Source: {src}",
            f"Destination: {self.destination_path or 'No destination selected'}",
            "Files recovered: 0 (no operation performed)",
            "Status: Preview only",
        ]:
            line = Gtk.Label(label=label)
            line.set_xalign(0)
            line.set_line_wrap(True)
            summary.pack_start(line, False, False, 0)
        self.recovery_body.pack_start(summary, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.pack_start(self.add_button("Back to safety review", lambda _b: self.change_recovery_step(2), False, "go-previous-symbolic"), False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        nav.pack_start(self.add_button("Start again", self.restart_recovery, True, "view-refresh-symbolic"), False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def change_recovery_step(self, step):
        self.recovery_step = step
        self.rerender_recovery()

    def restart_recovery(self, _button):
        self.recovery_step = 0
        self.selected_disk = None
        self.destination_path = ""
        self.results_preview = False
        self.show_page("Recovery")
        self.load_real_disks_async()

    # ---------- Informational pages ----------
    def show_drive_health(self):
        self.page_heading("Diagnostics", "Drive Health", "Health checks are not connected in this prototype. No S.M.A.R.T. commands are run.")
        self.content.pack_start(self.make_card(
            "S.M.A.R.T. health", "Drive-health data may help identify a failing device, but it is not a guarantee that data is safe.",
            "Not connected", "utilities-system-monitor-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Important note", "If a drive may be failing, minimize unnecessary use and avoid running write-based repair tools before data has been secured.",
            "Information only", "dialog-information-symbolic"
        ), False, False, 0)

    def show_tools(self):
        self.page_heading("Utilities", "System Tools", "Additional tools will be connected only after their safety behavior can be tested.")
        self.content.pack_start(self.make_card(
            "Antivirus scan", "ClamAV integration is not connected. No files are scanned.",
            "Unavailable in this build", "system-search-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Safe eject", "Device unmounting and eject controls are not connected. No device can be ejected from this screen.",
            "Unavailable in this build", "media-eject-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Windows boot repair", "Future feature. Any repair workflow must be explicitly separated from file recovery and must clearly explain write operations.",
            "Not implemented", "applications-system-symbolic"
        ), False, False, 0)

    def show_about(self):
        self.page_heading("Project information", "About Rescue-OS", "A recovery environment designed to make recovery steps understandable and protect original data.")
        self.content.pack_start(self.make_card(
            "Current build", f"{APP_NAME} — {APP_VERSION}\nPython 3 · GTK 3 · Alpine Linux / XFCE",
            "UI/UX prototype with live device metadata", "help-about-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Design principles",
            "1. Make the next step clear.\n2. Explain risks before actions.\n3. Verify read-only behavior in the backend.\n4. Never claim success without backend confirmation.\n5. Never mount or modify a device during discovery.",
            None, "security-high-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Current limitations",
            "The application only reads lsblk metadata and previews the workflow. It does not mount filesystems, browse source files, copy data, repair filesystems, run antivirus scans, or invoke Rescue-Drive.sh.",
            "Do not use as a recovery tool yet", "dialog-warning-symbolic"
        ), False, False, 0)

    # ---------- Styling ----------
    def apply_css(self):
        css = b"""
        window { background: #f3f6fa; color: #192536; }
        .sidebar { background: #172435; color: #f7f9fc; }
        .sidebar label { color: #f7f9fc; }
        .sidebar image { color: #c7d6e8; }
        .sidebar-muted { color: #a8b7c9; font-size: 10pt; }
        .nav-button { color: #dce6f1; background: transparent; border: 1px solid transparent; border-radius: 9px; padding: 11px 12px; }
        .nav-button:hover { background: #27394f; }
        .nav-button.active { background: #314d6b; border: 1px solid #466684; color: #ffffff; }
        .sidebar-note { background: #202f43; border: 1px solid #35475e; border-radius: 12px; }
        .sidebar-note-title { font-weight: bold; }
        .eyebrow { color: #466b91; font-size: 9pt; font-weight: bold; }
        .muted { color: #65758a; }
        .card { background: #ffffff; border: 1px solid #dce4ed; border-radius: 12px; }
        .card label { color: #192536; }
        .hero-card { background: #e6eff9; border: 1px solid #cfdeee; border-radius: 14px; }
        .subtle-row { background: #ffffff; border: 1px solid #e0e7ef; border-radius: 10px; }
        .status-neutral { color: #34577a; background: #e9f1f9; border-radius: 7px; padding: 5px 8px; font-size: 9pt; }
        .size-badge { color: #314b66; background: #edf2f7; border-radius: 7px; padding: 7px 9px; font-weight: bold; }
        .disk-list { background: transparent; }
        .disk-list row { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; margin: 4px 0; }
        .disk-list row:hover { border: 1px solid #9bb7d4; }
        .disk-list row:selected { background: #e5effb; border: 1px solid #7da5cf; }
        .disk-list row:selected label { color: #192536; }
        .step-item { background: #e9eef4; border: 1px solid #dce4ed; border-radius: 10px; }
        .step-current { background: #deebfa; border: 1px solid #a8c5e4; }
        .step-done { background: #e8f2ee; border: 1px solid #c8ded4; }
        .step-number { background: #ffffff; border: 1px solid #ccd7e3; border-radius: 14px; color: #36516e; font-weight: bold; }
        .step-current .step-number { background: #245b8f; border: 1px solid #245b8f; color: #ffffff; }
        .step-label { font-size: 9pt; font-weight: bold; }
        .review-row { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; }
        .review-icon { background: #edf2f7; border-radius: 14px; color: #405b76; font-weight: bold; }
        .review-warning { background: #fffaf0; border: 1px solid #f0ddb0; }
        .review-warning .review-icon { background: #f8e8bd; color: #7b5710; }
        .review-pending .review-icon { background: #e3edf8; color: #315c87; }
        .warning-text { color: #805914; background: #fff7e6; border: 1px solid #f0ddb0; border-radius: 8px; padding: 10px; }
        .error-text { color: #9e2f2f; background: #fff0f0; border: 1px solid #edc6c6; border-radius: 8px; padding: 12px; }
        button { border-radius: 8px; padding: 8px 12px; }
        button.suggested-action { background: #245b8f; color: #ffffff; border: 1px solid #245b8f; font-weight: bold; }
        button.suggested-action:hover { background: #1d4b77; }
        button:disabled { opacity: 0.55; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def main():
    window = RescueOSWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

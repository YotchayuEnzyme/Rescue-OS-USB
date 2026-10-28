#!/usr/bin/env python3
"""Rescue-OS GUI Prototype v0.5.1 — GNOME Disks style source confirmation.

Safety scope:
- Reads block-device metadata through lsblk only.
- Does not mount, unmount, repair, format, scan, eject, copy, or write to disks.
- The recovery wizard is a UI workflow preview, not a recovery implementation.
- Selecting a destination only opens a folder chooser; no files are created.
- Read-only status and source/destination separation are NOT verified by this prototype.

Requirements on Alpine Linux:
    apk add python3 py3-gobject3 gtk+3.0 util-linux
    python3 /root/Desktop/rescue_gui.py
"""

import json
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

APP_NAME = "Rescue-OS"
APP_VERSION = "Prototype v0.5.1"


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


def get_partition_color_class(fstype):
    """Return CSS color suffix based on filesystem type."""
    fs = str(fstype or "").lower()
    if fs in ("fat", "vfat", "fat32", "fat16", "ntfs", "msftres", "efi", "exfat"):
        return "purple"
    elif fs in ("ext2", "ext3", "ext4", "xfs", "btrfs"):
        return "orange"
    elif "lvm" in fs or "luks" in fs or "crypto" in fs:
        return "red"
    else:
        return "grey"


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
        super().__init__(title=f"{APP_NAME} - {APP_VERSION}")
        self.set_default_size(850, 520)
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
        self.source_confirmed = False
        self.destination_path = ""
        self.recovery_step = 0
        self.results_preview = False

        self.disk_list_box = None
        self.disk_count_label = None
        self.disk_detail_box = None
        self.recovery_body = None
        self.recovery_step_buttons = []
        self.recovery_continue_button = None
        self.source_confirm_checkbox = None
        self.source_confirm_continue_button = None
        self.destination_label = None

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)
        root.pack_start(self.build_sidebar(), False, False, 0)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_min_content_width(340)
        root.pack_start(self.scroller, True, True, 0)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_border_width(16)
        self.scroller.add(self.content)

        self.apply_css()
        self.show_page("Dashboard")

    # ---------- Shared widgets ----------
    def build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(180, -1)
        sidebar.set_border_width(12)
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
        brand.set_margin_bottom(24)
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

        safety_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        safety_card.set_border_width(10)
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
        version.set_margin_top(8)
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
        body_label.set_max_width_chars(75)
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
        self.source_confirm_checkbox = None
        self.source_confirm_continue_button = None
        self.destination_label = None
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
            "System", "Alpine Linux / XFCE",
            "Environment ready", "computer-symbolic"
        ), True, True, 0)
        quick_cards.pack_start(self.make_card(
            "Storage", "Read via lsblk",
            "Read-only discovery", "drive-harddisk-symbolic"
        ), True, True, 0)
        quick_cards.pack_start(self.make_card(
            "Safety", "No disk writes",
            "Prototype mode", "security-high-symbolic"
        ), True, True, 0)
        self.content.pack_start(quick_cards, False, False, 0)

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        hero.set_border_width(20)
        hero.get_style_context().add_class("hero-card")
        hero_label = Gtk.Label(label="RECOVER FILES")
        hero_label.set_xalign(0)
        hero_label.get_style_context().add_class("eyebrow")
        hero.pack_start(hero_label, False, False, 0)
        hero_title = Gtk.Label()
        hero_title.set_markup('<span size="x-large" weight="bold">Find and inspect a source device</span>')
        hero_title.set_xalign(0)
        hero.pack_start(hero_title, False, False, 0)
        hero_desc = Gtk.Label(
            label="Review detected disks, inspect partition allocation in a visual layout, and choose a destination folder."
        )
        hero_desc.set_xalign(0)
        hero_desc.set_line_wrap(True)
        hero.pack_start(hero_desc, False, False, 0)
        hero_button = self.add_button("Open Recovery", lambda _b: self.show_page("Recovery"), True, "go-next-symbolic")
        hero_button.set_halign(Gtk.Align.START)
        hero.pack_start(hero_button, False, False, 0)
        self.content.pack_start(hero, False, False, 0)

    # ---------- Recovery wizard ----------
    def show_recovery(self):
        self.page_heading(
            "Guided workflow", "Recover Files",
            "Review the workflow step by step. This prototype discovers devices without modifying disks."
        )
        self.build_stepper()
        self.recovery_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.content.pack_start(self.recovery_body, True, True, 0)
        self.render_recovery_step()

    def build_stepper(self):
        names = [
            "Select source", "Confirm source", "Destination",
            "Safety review", "Summary",
        ]
        current = max(0, min(self.recovery_step, len(names) - 1))
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        wrapper.set_border_width(10)
        wrapper.get_style_context().add_class("stepper-card")

        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label()
        label.set_markup(
            f'<span weight="bold">STEP {current + 1} OF {len(names)}</span>'
            f'  -  {escape_markup(names[current])}'
        )
        label.set_xalign(0)
        line.pack_start(label, True, True, 0)
        wrapper.pack_start(line, False, False, 0)

        progress = Gtk.ProgressBar()
        progress.set_fraction((current + 1) / len(names))
        progress.set_show_text(False)
        progress.set_size_request(-1, 5)
        wrapper.pack_start(progress, False, False, 0)
        self.content.pack_start(wrapper, False, False, 0)

    def rerender_recovery(self):
        if self.current_page != "Recovery":
            return
        self.show_page("Recovery")

    def render_recovery_step(self):
        self.clear_box(self.recovery_body)
        if self.recovery_step == 0:
            self.render_source_step()
        elif self.recovery_step == 1:
            self.render_source_confirmation_step()
        elif self.recovery_step == 2:
            self.render_destination_step()
        elif self.recovery_step == 3:
            self.render_safety_step()
        else:
            self.render_results_step()
        self.recovery_body.show_all()

    def render_source_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Choose the drive that contains your files",
            "Select a device below to inspect its capacity, model, and partition layout.",
            "Read-only metadata discovery via lsblk.",
            "drive-harddisk-symbolic"
        ), False, False, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        refresh = self.add_button("Refresh", self.on_refresh_disks, False, "view-refresh-symbolic")
        toolbar.pack_start(refresh, False, False, 0)
        self.disk_count_label = Gtk.Label(label="Reading device information...")
        self.disk_count_label.set_xalign(0)
        self.disk_count_label.set_line_wrap(True)
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

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.pack_start(Gtk.Box(), True, True, 0)
        self.recovery_continue_button = self.add_button(
            "Review selected drive", self.on_review_source, True, "go-next-symbolic"
        )
        self.recovery_continue_button.set_sensitive(self.selected_disk is not None)
        nav.pack_start(self.recovery_continue_button, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

        self.render_disk_rows()
        if self.disk_load_state == "idle":
            self.load_real_disks_async()
        elif self.disk_load_state == "loading":
            self.disk_count_label.set_text("Reading device information...")
        elif self.disk_load_state == "loaded":
            self.disk_count_label.set_text(f"{len(self.disk_cache)} device(s) detected")
        elif self.disk_load_state == "error":
            self.disk_count_label.set_text("Device information could not be read")
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
            detail_text = f"{path}  |  {transport}  |  {partition_count} partition(s)"
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
            self.source_confirmed = False
            if self.disk_detail_box:
                self.clear_box(self.disk_detail_box)
            if self.recovery_continue_button:
                self.recovery_continue_button.set_sensitive(False)
            return

        disk = self.disk_data_by_row.get(row)
        if not disk:
            return

        current_path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
        old_path = None
        if self.selected_disk:
            old_path = self.selected_disk.get("path") or (
                "/dev/" + str(self.selected_disk.get("name", "unknown"))
            )
        if current_path != old_path:
            self.source_confirmed = False
            if old_path is not None:
                self.destination_path = ""
        self.selected_disk = disk

        if self.recovery_continue_button:
            self.recovery_continue_button.set_sensitive(True)
        if self.disk_detail_box is None:
            return

        self.clear_box(self.disk_detail_box)
        partitions = disk.get("children") or []
        summary_line = (
            f"Selected: {current_path} ({format_bytes(disk.get('size'))}) - "
            f"{len(partitions)} partition(s) detected. Click 'Review selected drive' to inspect layout."
        )
        self.disk_detail_box.pack_start(self.make_card(
            "Drive ready for inspection", summary_line,
            "Click 'Review selected drive' to continue",
            "drive-harddisk-symbolic"
        ), False, False, 0)
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
            self.disk_count_label.set_text("Reading device information...")
        if self.disk_list_box:
            self.clear_box(self.disk_list_box)
            loading = Gtk.Label(label="Scanning visible block devices...")
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
        old_path = None
        if self.selected_disk:
            old_path = self.selected_disk.get("path") or ("/dev/" + str(self.selected_disk.get("name", "unknown")))
        self.selected_disk = None
        self.source_confirmed = False
        self.render_disk_rows()
        reselected = False
        if old_path:
            for row, disk in self.disk_data_by_row.items():
                path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
                if path == old_path:
                    self.disk_list_box.select_row(row)
                    reselected = True
                    break
        if old_path and not reselected:
            self.destination_path = ""
        self.content.show_all()
        return GLib.SOURCE_REMOVE

    def on_review_source(self, _button):
        if self.selected_disk is None:
            return
        self.source_confirmed = False
        self.recovery_step = 1
        self.rerender_recovery()

    def render_source_confirmation_step(self):
        """Step 2: GNOME Disks style visual layout for drive verification."""
        if self.selected_disk is None:
            self.recovery_step = 0
            self.rerender_recovery()
            return

        disk = self.selected_disk
        device_path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
        display_name = disk.get("model") or disk.get("label") or disk.get("name") or "Disk Drive"
        total_size = max(1, int(disk.get("size") or 1))

        # Main GNOME Disks style container card
        gnome_disks_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        gnome_disks_card.set_border_width(20)
        gnome_disks_card.get_style_context().add_class("card")

        # 1. Top Drive Header (Large Icon + Size/Model + Action buttons)
        top_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        disk_large_image = Gtk.Image.new_from_icon_name("drive-harddisk", Gtk.IconSize.DIALOG)
        disk_large_image.set_pixel_size(64)
        top_info.pack_start(disk_large_image, False, False, 0)

        title_desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_desc_box.set_valign(Gtk.Align.CENTER)
        large_title = Gtk.Label()
        large_title.set_markup(
            f'<span size="x-large" weight="bold">{escape_markup(format_bytes(total_size))} {escape_markup(display_name)}</span>'
        )
        large_title.set_xalign(0)
        sub_text = Gtk.Label(label=device_path)
        sub_text.get_style_context().add_class("muted")
        sub_text.set_xalign(0)
        title_desc_box.pack_start(large_title, False, False, 0)
        title_desc_box.pack_start(sub_text, False, False, 0)
        top_info.pack_start(title_desc_box, True, True, 0)

        top_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top_actions.set_valign(Gtk.Align.CENTER)
        info_btn = Gtk.Button()
        info_btn.set_tooltip_text("Drive details (Read-only)")
        info_btn.set_image(Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.BUTTON))
        top_actions.pack_start(info_btn, False, False, 0)
        more_btn = Gtk.Button()
        more_btn.set_tooltip_text("More options")
        more_btn.set_image(Gtk.Image.new_from_icon_name("view-more-symbolic", Gtk.IconSize.BUTTON))
        top_actions.pack_start(more_btn, False, False, 0)
        top_info.pack_start(top_actions, False, False, 0)
        gnome_disks_card.pack_start(top_info, False, False, 0)

        # 2. Space Allocation Bar
        alloc_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        alloc_title = Gtk.Label()
        alloc_title.set_markup('<span weight="bold">Space Allocation</span>')
        alloc_title.set_xalign(0)
        alloc_vbox.pack_start(alloc_title, False, False, 0)

        partitions = disk.get("children") or []
        alloc_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        alloc_strip.get_style_context().add_class("allocation-strip")
        alloc_strip.set_size_request(-1, 20)

        processed_size = 0
        total_box_width = 720
        for part in partitions:
            part_size = int(part.get("size") or 0)
            processed_size += part_size
            ratio = max(0.03, min(1.0, part_size / total_size))
            color_class = get_partition_color_class(part.get("fstype", ""))

            part_segment = Gtk.EventBox()
            part_segment.get_style_context().add_class(f"alloc-{color_class}")
            part_segment.set_size_request(max(14, int(total_box_width * ratio)), 20)
            part_segment.set_tooltip_text(
                f"{part.get('name', '')}: {format_bytes(part_size)} ({part.get('fstype') or 'Unknown FS'})"
            )
            alloc_strip.pack_start(part_segment, True, True, 0)

        free_space = max(0, total_size - processed_size)
        if free_space > (1024 * 1024 * 50) or not partitions:
            ratio = max(0.05, free_space / total_size) if partitions else 1.0
            unalloc_segment = Gtk.EventBox()
            unalloc_segment.get_style_context().add_class("alloc-grey")
            unalloc_segment.set_size_request(max(18, int(total_box_width * ratio)), 20)
            unalloc_segment.set_tooltip_text(f"Free Space: {format_bytes(free_space)}")
            alloc_strip.pack_start(unalloc_segment, True, True, 0)

        alloc_vbox.pack_start(alloc_strip, False, False, 0)
        gnome_disks_card.pack_start(alloc_vbox, False, False, 0)

        # 3. Volumes List
        volumes_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vol_title = Gtk.Label()
        vol_title.set_markup('<span weight="bold">Volumes</span>')
        vol_title.set_xalign(0)
        volumes_vbox.pack_start(vol_title, False, False, 0)

        vol_list = Gtk.ListBox()
        vol_list.set_selection_mode(Gtk.SelectionMode.NONE)
        vol_list.get_style_context().add_class("volume-list")

        if not partitions:
            empty_row = Gtk.ListBoxRow()
            empty_row.get_style_context().add_class("volume-row")
            empty_label = Gtk.Label(label="No partitions reported on this device.")
            empty_label.set_xalign(0)
            empty_label.set_margin_top(10)
            empty_label.set_margin_bottom(10)
            empty_label.set_margin_start(12)
            empty_label.get_style_context().add_class("muted")
            empty_row.add(empty_label)
            vol_list.add(empty_row)
        else:
            for part in partitions:
                part_row = Gtk.ListBoxRow()
                part_row.get_style_context().add_class("volume-row")

                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_box.set_border_width(12)

                color_class = get_partition_color_class(part.get("fstype", ""))
                color_dot = Gtk.Box()
                color_dot.get_style_context().add_class(f"vol-dot-{color_class}")
                color_dot.set_size_request(14, 14)
                color_dot.set_valign(Gtk.Align.CENTER)
                row_box.pack_start(color_dot, False, False, 0)

                text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                fs = (part.get("fstype") or "Unknown FS").upper()
                label = part.get("label")
                title_str = f"{format_bytes(part.get('size'))} {fs}"
                if label:
                    title_str += f" ({label})"

                mount = part.get("mountpoint") or part.get("path") or "-"

                name_lbl = Gtk.Label()
                name_lbl.set_markup(f'<span weight="bold">{escape_markup(title_str)}</span>')
                name_lbl.set_xalign(0)
                meta_lbl = Gtk.Label(label=str(mount))
                meta_lbl.get_style_context().add_class("muted")
                meta_lbl.set_xalign(0)

                text_box.pack_start(name_lbl, False, False, 0)
                text_box.pack_start(meta_lbl, False, False, 0)
                row_box.pack_start(text_box, True, True, 0)

                # Relative size bar on the right
                part_size = int(part.get("size") or 0)
                rel_ratio = max(0.08, min(1.0, part_size / total_size))
                vol_progress = Gtk.ProgressBar()
                vol_progress.set_fraction(rel_ratio)
                vol_progress.set_size_request(130, 8)
                vol_progress.set_valign(Gtk.Align.CENTER)
                row_box.pack_start(vol_progress, False, False, 0)

                part_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                part_menu_btn = Gtk.Button()
                part_menu_btn.set_relief(Gtk.ReliefStyle.NONE)
                part_menu_btn.set_image(Gtk.Image.new_from_icon_name("view-more-symbolic", Gtk.IconSize.BUTTON))
                part_actions.pack_start(part_menu_btn, False, False, 0)
                part_expand_btn = Gtk.Button()
                part_expand_btn.set_relief(Gtk.ReliefStyle.NONE)
                part_expand_btn.set_image(Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON))
                part_actions.pack_start(part_expand_btn, False, False, 0)
                row_box.pack_start(part_actions, False, False, 0)

                part_row.add(row_box)
                vol_list.add(part_row)

        volumes_vbox.pack_start(vol_list, False, False, 0)
        gnome_disks_card.pack_start(volumes_vbox, False, False, 0)

        self.recovery_body.pack_start(gnome_disks_card, False, False, 0)

        # 4. Confirmation checkbox and navigation
        confirm = Gtk.CheckButton(label="I confirm this is the correct source drive to recover from.")
        confirm.set_active(self.source_confirmed)
        confirm.connect("toggled", self.on_source_confirmation_toggled)
        self.source_confirm_checkbox = confirm
        self.recovery_body.pack_start(confirm, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.pack_start(self.add_button("Back to drive list", lambda _b: self.change_recovery_step(0), False, "go-previous-symbolic"), False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        self.source_confirm_continue_button = self.add_button(
            "Confirm & choose destination", self.on_confirm_source_to_destination,
            True, "go-next-symbolic"
        )
        self.source_confirm_continue_button.set_sensitive(self.source_confirmed)
        nav.pack_start(self.source_confirm_continue_button, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def on_source_confirmation_toggled(self, checkbox):
        self.source_confirmed = checkbox.get_active()
        if self.source_confirm_continue_button:
            self.source_confirm_continue_button.set_sensitive(self.source_confirmed)

    def on_confirm_source_to_destination(self, _button):
        if self.selected_disk is None or not self.source_confirmed:
            return
        self.recovery_step = 2
        self.rerender_recovery()

    def render_destination_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Choose a destination folder",
            "Recovered files must be saved to a separate drive. Selecting a folder in this prototype does not write any files.",
            "Destination separation is not verified automatically yet.", "folder-symbolic"
        ), False, False, 0)

        if self.selected_disk is None or not self.source_confirmed:
            self.recovery_step = 0
            self.rerender_recovery()
            return
        selected_path = self.selected_disk.get("path") or ("/dev/" + str(self.selected_disk.get("name", "unknown")))
        selected_name = self.selected_disk.get("model") or self.selected_disk.get("label") or self.selected_disk.get("name") or "Selected drive"
        source_card = self.make_card(
            "Confirmed source",
            f"{selected_name}\n{selected_path} ({format_bytes(self.selected_disk.get('size'))})",
            "Confirmed by user", "drive-harddisk-symbolic"
        )
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
        choose = self.add_button("Choose folder...", self.on_choose_destination, False, "folder-open-symbolic")
        path_row.pack_start(choose, False, False, 0)
        dest_box.pack_start(path_row, False, False, 0)
        self.recovery_body.pack_start(dest_box, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        back = self.add_button("Back to source layout", lambda _b: self.change_recovery_step(1), False, "go-previous-symbolic")
        nav.pack_start(back, False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        next_button = self.add_button("Continue to safety review", lambda _b: self.change_recovery_step(3), True, "go-next-symbolic")
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
            "Review the summary below before starting any recovery operation.",
            "Recovery is not connected in this prototype", "security-high-symbolic"
        ), False, False, 0)

        source = self.selected_disk.get("path", "Unknown") if self.selected_disk else "No source selected"
        source_status = "User confirmed this source" if self.source_confirmed else "Not confirmed"
        self.recovery_body.pack_start(self.make_review_row("Source drive", f"{source} - {source_status}", "review-pending"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Destination folder", self.destination_path or "Not selected", "review-pending"), False, False, 0)
        self.recovery_body.pack_start(self.make_review_row("Read-only mount verification", "NOT VERIFIED - backend check pending", "review-warning"), False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        back = self.add_button("Back to destination", lambda _b: self.change_recovery_step(2), False, "go-previous-symbolic")
        preview = self.add_button("Preview summary", lambda _b: self.show_result_preview(), True, "go-next-symbolic")
        nav.pack_start(back, False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        nav.pack_start(preview, False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def make_review_row(self, title, detail, style_class):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_border_width(13)
        row.get_style_context().add_class("review-row")
        status = Gtk.Label(label="!" if style_class == "review-warning" else "*")
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
        self.recovery_step = 4
        self.rerender_recovery()

    def render_results_step(self):
        self.recovery_body.pack_start(self.make_card(
            "Recovery results preview",
            "This is a UI preview only. No files have been copied or modified.",
            "PREVIEW ONLY", "document-properties-symbolic"
        ), False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.pack_start(self.add_button("Back to safety review", lambda _b: self.change_recovery_step(3), False, "go-previous-symbolic"), False, False, 0)
        nav.pack_start(Gtk.Box(), True, True, 0)
        nav.pack_start(self.add_button("Start again", self.restart_recovery, True, "view-refresh-symbolic"), False, False, 0)
        self.recovery_body.pack_start(nav, False, False, 0)

    def change_recovery_step(self, step):
        self.recovery_step = step
        self.rerender_recovery()

    def restart_recovery(self, _button):
        self.recovery_step = 0
        self.selected_disk = None
        self.source_confirmed = False
        self.destination_path = ""
        self.results_preview = False
        self.show_page("Recovery")
        self.load_real_disks_async()

    # ---------- Informational pages ----------
    def show_drive_health(self):
        self.page_heading("Diagnostics", "Drive Health", "S.M.A.R.T. checks are not connected in this prototype.")
        self.content.pack_start(self.make_card(
            "S.M.A.R.T. health", "Drive health diagnostics will be integrated in a future build.",
            "Not connected", "utilities-system-monitor-symbolic"
        ), False, False, 0)

    def show_tools(self):
        self.page_heading("Utilities", "System Tools", "Additional tools will be connected after testing.")
        self.content.pack_start(self.make_card(
            "Antivirus scan (ClamAV)", "Detection and reporting only. Not connected yet.",
            "Unavailable in prototype", "system-search-symbolic"
        ), False, False, 0)
        self.content.pack_start(self.make_card(
            "Safe eject", "Unmount and power-off controls are not connected yet.",
            "Unavailable in prototype", "media-eject-symbolic"
        ), False, False, 0)

    def show_about(self):
        self.page_heading("Project information", "About Rescue-OS", "A read-only focused recovery environment.")
        self.content.pack_start(self.make_card(
            "Current build", f"{APP_NAME} - {APP_VERSION}\nPython 3 + GTK 3 on Alpine Linux",
            "UI prototype with lsblk discovery", "help-about-symbolic"
        ), False, False, 0)

    # ---------- Styling ----------
    def apply_css(self):
        css = b"""
        window { background: #f3f6fa; color: #192536; }
        .sidebar { background: #172435; color: #f7f9fc; }
        .sidebar label { color: #f7f9fc; }
        .sidebar image { color: #c7d6e8; }
        .sidebar-muted { color: #a8b7c9; font-size: 10pt; }
        .nav-button { color: #dce6f1; background: transparent; border: 1px solid transparent; border-radius: 9px; padding: 10px 12px; }
        .nav-button:hover { background: #27394f; }
        .nav-button.active { background: #314d6b; border: 1px solid #466684; color: #ffffff; }
        .sidebar-note { background: #202f43; border: 1px solid #35475e; border-radius: 12px; }
        .sidebar-note-title { font-weight: bold; }
        .eyebrow { color: #466b91; font-size: 9pt; font-weight: bold; }
        .muted { color: #65758a; }
        .card { background: #ffffff; border: 1px solid #dce4ed; border-radius: 12px; }
        .card label { color: #192536; }
        .hero-card { background: #e6eff9; border: 1px solid #cfdeee; border-radius: 14px; }
        .status-neutral { color: #34577a; background: #e9f1f9; border-radius: 7px; padding: 5px 8px; font-size: 9pt; }
        .size-badge { color: #314b66; background: #edf2f7; border-radius: 7px; padding: 7px 9px; font-weight: bold; }
        .disk-list { background: transparent; }
        .disk-list row { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; margin: 4px 0; }
        .disk-list row:hover { border: 1px solid #9bb7d4; }
        .disk-list row:selected { background: #e5effb; border: 1px solid #7da5cf; }
        .disk-list row:selected label { color: #192536; }
        .stepper-card { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; }
        .stepper-card progress { min-height: 5px; border-radius: 3px; }
        .review-row { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; }
        .review-icon { background: #edf2f7; border-radius: 14px; color: #405b76; font-weight: bold; }
        .review-warning { background: #fffaf0; border: 1px solid #f0ddb0; }
        .review-warning .review-icon { background: #f8e8bd; color: #7b5710; }
        .review-pending .review-icon { background: #e3edf8; color: #315c87; }
        .error-text { color: #9e2f2f; background: #fff0f0; border: 1px solid #edc6c6; border-radius: 8px; padding: 12px; }

        /* GNOME Disks layout styles */
        .allocation-strip { background: #e0e6ed; border-radius: 8px; min-height: 20px; border: 1px solid #ccd5e0; padding: 1px; }
        .alloc-purple { background: #8e24aa; border-radius: 4px; }
        .alloc-orange { background: #fb8c00; border-radius: 4px; }
        .alloc-red { background: #e53935; border-radius: 4px; }
        .alloc-grey { background: #9e9e9e; border-radius: 4px; }

        .volume-list { background: #ffffff; border: 1px solid #dce4ed; border-radius: 10px; }
        .volume-row { background: #ffffff; border-bottom: 1px solid #eef2f6; padding: 2px; }
        .vol-dot-purple { background: #8e24aa; border-radius: 99px; }
        .vol-dot-orange { background: #fb8c00; border-radius: 99px; }
        .vol-dot-red { background: #e53935; border-radius: 99px; }
        .vol-dot-grey { background: #9e9e9e; border-radius: 99px; }

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
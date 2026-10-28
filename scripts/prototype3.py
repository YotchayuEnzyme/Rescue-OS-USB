#!/usr/bin/env python3
# Rescue-OS GUI Prototype v0.3 (Bilingual EN/TH, real disk discovery)
# Python 3 + GTK 3 (PyGObject)
#
# Safety scope:
# - Reads device metadata using lsblk only.
# - Does NOT mount, unmount, format, repair, scan, eject, or write to disks.
# - Does NOT call Rescue-Drive.sh yet.
# - lsblk's RO field is only a block-device flag; it is NOT proof that a filesystem is mounted read-only.

import json
import shutil
import subprocess

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

APP_NAME = "Rescue-OS"
APP_VERSION = "Prototype v0.3"

STRINGS = {
    "en": {
        "subtitle_brand": "Recovery environment",
        "nav_dashboard": "Dashboard", "nav_dashboard_tip": "Overview",
        "nav_recovery": "Recovery", "nav_recovery_tip": "Disk discovery",
        "nav_tools": "Tools", "nav_tools_tip": "System tools",
        "nav_about": "About", "nav_about_tip": "About this prototype",
        "lang_btn": "🌐 ภาษาไทย (TH)",
        "proto_note": "PROTOTYPE MODE\nNo disks are modified.",
        "dash_title": "Dashboard",
        "dash_sub": "Welcome to Rescue-OS. Review the environment before starting recovery.",
        "card_sys_title": "System", "card_sys_body": "Alpine Linux / XFCE",
        "card_sys_status": "Demo status",
        "card_stor_title": "Storage", "card_stor_body": "Disk-device discovery via lsblk",
        "card_stor_status": "Live device metadata",
        "card_safe_title": "Safety", "card_safe_body": "No mount or write commands are run",
        "card_safe_status": "Discovery only",
        "card_begin_title": "Before you begin",
        "card_begin_body": "This version lists detected disks and partitions only. It does not mount, repair, scan, eject, or recover files. Verify the correct source and destination before any future recovery operation.",
        "btn_open_recovery": "Open Recovery",
        "rec_title": "Recovery",
        "rec_sub": "Detected block devices are shown below. This screen only reads device metadata.",
        "rec_safe_title": "Safety check",
        "rec_safe_body": "This screen calls lsblk to inspect device metadata. It does not mount or write to disks.",
        "rec_safe_status": "Discovery only — no recovery actions",
        "btn_refresh": "Refresh disk list",
        "disk_count": "Detected disk devices: {count}",
        "loading": "Reading device metadata…",
        "empty_disks": "No physical disks were returned by lsblk.",
        "lsblk_missing": "The 'lsblk' command was not found. Install util-linux and try again.",
        "lsblk_failed": "Could not read disk information. Details: {error}",
        "unknown": "Unknown",
        "not_available": "Not reported",
        "disk_size": "Size: {value}",
        "disk_device": "Device: {value}",
        "disk_model": "Model: {value}",
        "disk_transport": "Connection: {value}",
        "disk_removable": "Removable: {value}",
        "yes": "Yes", "no": "No",
        "partition_heading": "Partitions",
        "no_partitions": "No partitions reported for this device.",
        "partition_line": "{path} · {size} · Filesystem: {fs} · Label: {label} · Mounted at: {mount}",
        "device_ro": "Kernel block-device RO flag: {value}",
        "ro_yes": "Yes (device flag only)",
        "ro_no": "No (device flag only)",
        "ro_unknown": "Unknown",
        "safety_ro_note": "Important: the RO flag above does not prove a filesystem is mounted read-only.",
        "rec_note": "Next step: verify read-only behavior in the backend before adding any mount or backup action.",
        "tools_title": "System tools",
        "tools_sub": "Tool integrations will be added after the GUI structure and safety checks are tested.",
        "tool_smart_title": "S.M.A.R.T. status",
        "tool_smart_body": "Not connected yet. No drive health commands are run.",
        "tool_av_title": "Antivirus scan (ClamAV)",
        "tool_av_body": "Not connected yet. No files are scanned.",
        "tool_eject_title": "Safe eject",
        "tool_eject_body": "Not connected yet. No devices can be ejected from this screen.",
        "tool_unavail": "Unavailable in prototype",
        "about_title": "About Rescue-OS",
        "about_sub": "A recovery environment focused on understandable workflows and protecting source data.",
        "about_build_title": "Current build", "about_build_status": "Interface and disk-discovery demo",
        "about_prin_title": "Design principles",
        "about_prin_body": "1. Make the next step clear.\n2. Explain risks before actions.\n3. Verify read-only status in the backend, not just in the UI.\n4. Never claim a recovery action succeeded until the backend confirms it.\n5. Disk discovery must not automatically mount or modify a device.",
    },
    "th": {
        "subtitle_brand": "ระบบกู้คืนข้อมูลฉุกเฉิน",
        "nav_dashboard": "หน้าหลัก (Dashboard)", "nav_dashboard_tip": "ภาพรวมระบบ",
        "nav_recovery": "กู้ข้อมูล (Recovery)", "nav_recovery_tip": "ตรวจหารายการดิสก์",
        "nav_tools": "เครื่องมือ (Tools)", "nav_tools_tip": "เครื่องมือตรวจสอบระบบ",
        "nav_about": "เกี่ยวกับ (About)", "nav_about_tip": "ข้อมูลเกี่ยวกับรุ่นทดสอบนี้",
        "lang_btn": "🌐 English (EN)",
        "proto_note": "โหมดต้นแบบ (PROTOTYPE)\nไม่มีการ Mount หรือเขียนดิสก์",
        "dash_title": "หน้าหลัก (Dashboard)",
        "dash_sub": "ยินดีต้อนรับสู่ Rescue-OS ตรวจสอบสภาพแวดล้อมก่อนเริ่มกู้ข้อมูล",
        "card_sys_title": "ระบบปฏิบัติการ (System)", "card_sys_body": "Alpine Linux / XFCE",
        "card_sys_status": "สถานะระบบ",
        "card_stor_title": "พื้นที่จัดเก็บ (Storage)", "card_stor_body": "ตรวจพบอุปกรณ์ดิสก์ด้วย lsblk",
        "card_stor_status": "ข้อมูลอุปกรณ์จริง",
        "card_safe_title": "ความปลอดภัย (Safety)", "card_safe_body": "ไม่มีคำสั่ง Mount หรือเขียนดิสก์",
        "card_safe_status": "ตรวจสอบข้อมูลเท่านั้น",
        "card_begin_title": "ก่อนเริ่มต้นใช้งาน",
        "card_begin_body": "รุ่นนี้แสดงรายการดิสก์และพาร์ทิชันที่ตรวจพบเท่านั้น ยังไม่มีการ Mount ซ่อมแซม สแกน ถอดอุปกรณ์ หรือกู้ไฟล์ ต้องตรวจสอบดิสก์ต้นทางและปลายทางให้ถูกต้องก่อนเพิ่มขั้นตอนกู้ข้อมูลในอนาคต",
        "btn_open_recovery": "ไปยังหน้ากู้ข้อมูล (Open Recovery)",
        "rec_title": "กู้คืนข้อมูล (Recovery)",
        "rec_sub": "รายการด้านล่างมาจากอุปกรณ์ที่ระบบตรวจพบ หน้านี้อ่านเฉพาะข้อมูลอุปกรณ์",
        "rec_safe_title": "การตรวจสอบความปลอดภัย (Safety Check)",
        "rec_safe_body": "หน้านี้ใช้คำสั่ง lsblk อ่านข้อมูลอุปกรณ์เท่านั้น ไม่มีการ Mount หรือเขียนดิสก์",
        "rec_safe_status": "ตรวจพบอุปกรณ์เท่านั้น — ยังไม่กู้ข้อมูล",
        "btn_refresh": "รีเฟรชรายการดิสก์",
        "disk_count": "ตรวจพบอุปกรณ์ดิสก์: {count} รายการ",
        "loading": "กำลังอ่านข้อมูลอุปกรณ์…",
        "empty_disks": "lsblk ไม่พบรายการอุปกรณ์ประเภทดิสก์",
        "lsblk_missing": "ไม่พบคำสั่ง lsblk ให้ติดตั้งแพ็กเกจ util-linux แล้วลองใหม่",
        "lsblk_failed": "อ่านข้อมูลดิสก์ไม่สำเร็จ รายละเอียด: {error}",
        "unknown": "ไม่ทราบ",
        "not_available": "ไม่มีข้อมูล",
        "disk_size": "ขนาด: {value}",
        "disk_device": "อุปกรณ์: {value}",
        "disk_model": "รุ่น: {value}",
        "disk_transport": "การเชื่อมต่อ: {value}",
        "disk_removable": "อุปกรณ์ถอดได้: {value}",
        "yes": "ใช่", "no": "ไม่ใช่",
        "partition_heading": "พาร์ทิชัน",
        "no_partitions": "ระบบไม่รายงานพาร์ทิชันของอุปกรณ์นี้",
        "partition_line": "{path} · {size} · Filesystem: {fs} · Label: {label} · จุดเมานต์: {mount}",
        "device_ro": "สถานะ RO ของอุปกรณ์ระดับ Kernel: {value}",
        "ro_yes": "ใช่ (เป็นเพียงสถานะอุปกรณ์)",
        "ro_no": "ไม่ใช่ (เป็นเพียงสถานะอุปกรณ์)",
        "ro_unknown": "ไม่ทราบ",
        "safety_ro_note": "สำคัญ: ค่า RO ข้างต้นไม่ได้ยืนยันว่า Filesystem ถูก Mount แบบ Read-Only",
        "rec_note": "ขั้นถัดไป: ตรวจสอบ Read-Only จาก Backend ให้แน่นอนก่อนเพิ่มคำสั่ง Mount หรือสำรองไฟล์",
        "tools_title": "เครื่องมือระบบ (System Tools)",
        "tools_sub": "จะเชื่อมต่อเครื่องมือหลังจากทดสอบโครงสร้าง GUI และมาตรการความปลอดภัยแล้ว",
        "tool_smart_title": "ตรวจสุขภาพดิสก์ (S.M.A.R.T. Status)",
        "tool_smart_body": "ยังไม่ได้เชื่อมต่อ และไม่มีการเรียกคำสั่งตรวจสุขภาพดิสก์จริง",
        "tool_av_title": "สแกนไวรัส (Antivirus Scan)",
        "tool_av_body": "ยังไม่ได้เชื่อมต่อ และไม่มีการสแกนไฟล์จริง",
        "tool_eject_title": "ถอดไดรฟ์ปลอดภัย (Safe Eject)",
        "tool_eject_body": "ยังไม่ได้เชื่อมต่อ และยังสั่งถอดอุปกรณ์จากหน้านี้ไม่ได้",
        "tool_unavail": "ยังไม่เปิดใช้ในรุ่นต้นแบบ",
        "about_title": "เกี่ยวกับ Rescue-OS",
        "about_sub": "สภาพแวดล้อมกู้ข้อมูลที่เน้นขั้นตอนเข้าใจง่ายและการปกป้องข้อมูลต้นฉบับ",
        "about_build_title": "รุ่นปัจจุบัน (Current Build)", "about_build_status": "ต้นแบบ GUI และการตรวจพบดิสก์",
        "about_prin_title": "หลักการออกแบบ (Design Principles)",
        "about_prin_body": "1. แสดงขั้นตอนถัดไปให้เข้าใจง่าย\n2. อธิบายความเสี่ยงก่อนเริ่มทำงาน\n3. ตรวจสอบ Read-Only ใน Backend ไม่ใช่แค่บนหน้าจอ\n4. ไม่แจ้งว่ากู้ข้อมูลสำเร็จก่อน Backend ยืนยัน\n5. การตรวจพบดิสก์ต้องไม่ Mount หรือแก้ไขอุปกรณ์โดยอัตโนมัติ",
    },
}


def format_bytes(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unknown"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if number < 1000 or unit == units[-1]:
            if unit == "B":
                return f"{int(number)} {unit}"
            return f"{number:.1f} {unit}"
        number /= 1000.0
    return f"{number:.1f} PB"


class RescueOSWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=f"{APP_NAME} — {APP_VERSION}")
        self.set_default_size(1000, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)
        self.lang = "en"
        self.current_page = "Dashboard"
        self.nav_buttons = {}
        self.disk_list_box = None
        self.disk_count_label = None
        self.disk_detail_box = None
        self.disk_data_by_row = {}

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)
        root.pack_start(self.build_sidebar(), False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.pack_start(scroller, True, True, 0)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_border_width(28)
        scroller.add(self.content)

        self.apply_css()
        self.refresh_ui()

    def t(self, key, **kwargs):
        value = STRINGS[self.lang].get(key, key)
        return value.format(**kwargs) if kwargs else value

    def build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(230, -1)
        sidebar.set_border_width(18)
        sidebar.get_style_context().add_class("sidebar")
        self.brand_label = Gtk.Label()
        self.brand_label.set_xalign(0)
        self.brand_label.set_margin_bottom(24)
        sidebar.pack_start(self.brand_label, False, False, 0)

        for page_id, label_key, tip_key in [
            ("Dashboard", "nav_dashboard", "nav_dashboard_tip"),
            ("Recovery", "nav_recovery", "nav_recovery_tip"),
            ("Tools", "nav_tools", "nav_tools_tip"),
            ("About", "nav_about", "nav_about_tip"),
        ]:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_halign(Gtk.Align.FILL)
            button.connect("clicked", self.on_navigation_clicked, page_id)
            sidebar.pack_start(button, False, False, 0)
            self.nav_buttons[page_id] = (button, label_key, tip_key)

        sidebar.pack_start(Gtk.Box(), True, True, 0)
        self.lang_button = Gtk.Button()
        self.lang_button.get_style_context().add_class("lang-btn")
        self.lang_button.connect("clicked", self.on_toggle_language)
        sidebar.pack_start(self.lang_button, False, False, 6)
        self.safety_note = Gtk.Label()
        self.safety_note.set_xalign(0)
        self.safety_note.set_line_wrap(True)
        sidebar.pack_start(self.safety_note, False, False, 0)
        return sidebar

    def update_sidebar_text(self):
        self.brand_label.set_markup(
            f'<span size="large" weight="bold">{APP_NAME}</span>\n'
            f'<span size="small">{self.t("subtitle_brand")}</span>'
        )
        for _page_id, (button, label_key, tip_key) in self.nav_buttons.items():
            button.set_label(self.t(label_key))
            button.set_tooltip_text(self.t(tip_key))
        self.lang_button.set_label(self.t("lang_btn"))
        self.safety_note.set_markup(f'<span size="small">{self.t("proto_note")}</span>')

    def on_toggle_language(self, _button):
        self.lang = "th" if self.lang == "en" else "en"
        self.refresh_ui()

    def on_navigation_clicked(self, _button, page_name):
        self.current_page = page_name
        self.show_page(page_name)

    def refresh_ui(self):
        self.update_sidebar_text()
        self.show_page(self.current_page)

    def clear_content(self):
        for child in self.content.get_children():
            self.content.remove(child)
        self.disk_list_box = None
        self.disk_count_label = None
        self.disk_detail_box = None
        self.disk_data_by_row = {}

    def add_page_heading(self, title, subtitle):
        heading = Gtk.Label()
        heading.set_markup(f'<span size="xx-large" weight="bold">{title}</span>')
        heading.set_xalign(0)
        self.content.pack_start(heading, False, False, 0)
        description = Gtk.Label(label=subtitle)
        description.set_xalign(0)
        description.set_line_wrap(True)
        description.get_style_context().add_class("muted")
        self.content.pack_start(description, False, False, 0)

    def make_card(self, title, body, status=None):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_border_width(18)
        card.get_style_context().add_class("card")
        title_label = Gtk.Label()
        title_label.set_markup(f'<span weight="bold">{title}</span>')
        title_label.set_xalign(0)
        card.pack_start(title_label, False, False, 0)
        body_label = Gtk.Label(label=body)
        body_label.set_xalign(0)
        body_label.set_line_wrap(True)
        card.pack_start(body_label, False, False, 0)
        if status:
            status_label = Gtk.Label(label=status)
            status_label.set_xalign(0)
            status_label.set_line_wrap(True)
            status_label.get_style_context().add_class("status")
            card.pack_start(status_label, False, False, 0)
        return card

    def show_page(self, page_name):
        self.current_page = page_name
        self.clear_content()
        if page_name == "Dashboard":
            self.add_page_heading(self.t("dash_title"), self.t("dash_sub"))
            summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            summary.pack_start(self.make_card(self.t("card_sys_title"), self.t("card_sys_body"), self.t("card_sys_status")), True, True, 0)
            summary.pack_start(self.make_card(self.t("card_stor_title"), self.t("card_stor_body"), self.t("card_stor_status")), True, True, 0)
            summary.pack_start(self.make_card(self.t("card_safe_title"), self.t("card_safe_body"), self.t("card_safe_status")), True, True, 0)
            self.content.pack_start(summary, False, False, 0)
            self.content.pack_start(self.make_card(self.t("card_begin_title"), self.t("card_begin_body")), False, False, 0)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            recovery_button = Gtk.Button(label=self.t("btn_open_recovery"))
            recovery_button.get_style_context().add_class("suggested-action")
            recovery_button.connect("clicked", lambda _button: self.show_page("Recovery"))
            actions.pack_start(recovery_button, False, False, 0)
            self.content.pack_start(actions, False, False, 0)

        elif page_name == "Recovery":
            self.add_page_heading(self.t("rec_title"), self.t("rec_sub"))
            self.content.pack_start(self.make_card(self.t("rec_safe_title"), self.t("rec_safe_body"), self.t("rec_safe_status")), False, False, 0)

            toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            refresh_button = Gtk.Button(label=self.t("btn_refresh"))
            refresh_button.get_style_context().add_class("suggested-action")
            refresh_button.connect("clicked", self.on_refresh_disks)
            toolbar.pack_start(refresh_button, False, False, 0)
            self.disk_count_label = Gtk.Label(label=self.t("loading"))
            self.disk_count_label.set_xalign(0)
            self.disk_count_label.get_style_context().add_class("muted")
            toolbar.pack_start(self.disk_count_label, True, True, 0)
            self.content.pack_start(toolbar, False, False, 0)

            self.disk_list_box = Gtk.ListBox()
            self.disk_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.disk_list_box.get_style_context().add_class("disk-list")
            self.disk_list_box.connect("row-selected", self.on_disk_selected)
            self.content.pack_start(self.disk_list_box, False, False, 0)

            self.disk_detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            self.content.pack_start(self.disk_detail_box, False, False, 0)
            note = Gtk.Label(label=self.t("rec_note"))
            note.set_xalign(0)
            note.set_line_wrap(True)
            note.get_style_context().add_class("muted")
            self.content.pack_start(note, False, False, 0)
            self.load_real_disks()

        elif page_name == "Tools":
            self.add_page_heading(self.t("tools_title"), self.t("tools_sub"))
            for title_key, body_key in [("tool_smart_title", "tool_smart_body"), ("tool_av_title", "tool_av_body"), ("tool_eject_title", "tool_eject_body")]:
                self.content.pack_start(self.make_card(self.t(title_key), self.t(body_key), self.t("tool_unavail")), False, False, 0)

        elif page_name == "About":
            self.add_page_heading(self.t("about_title"), self.t("about_sub"))
            self.content.pack_start(self.make_card(self.t("about_build_title"), f"{APP_NAME} {APP_VERSION}", self.t("about_build_status")), False, False, 0)
            self.content.pack_start(self.make_card(self.t("about_prin_title"), self.t("about_prin_body")), False, False, 0)
        self.content.show_all()

    def on_refresh_disks(self, _button):
        self.load_real_disks()

    def load_real_disks(self):
        if self.disk_count_label is None or self.disk_list_box is None:
            return
        self.disk_count_label.set_text(self.t("loading"))
        for row in self.disk_list_box.get_children():
            self.disk_list_box.remove(row)
        self.disk_data_by_row = {}
        if self.disk_detail_box is not None:
            for child in self.disk_detail_box.get_children():
                self.disk_detail_box.remove(child)

        if not shutil.which("lsblk"):
            self.disk_count_label.set_text(self.t("lsblk_missing"))
            self.content.show_all()
            return

        # Fixed argument list; no shell is invoked. -b reports sizes in bytes.
        command = [
            "lsblk", "--json", "--bytes", "--output",
            "NAME,PATH,TYPE,SIZE,FSTYPE,LABEL,MODEL,TRAN,RM,RO,MOUNTPOINT"
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=8)
            if result.returncode != 0:
                message = result.stderr.strip() or f"lsblk exited with code {result.returncode}"
                raise RuntimeError(message)
            data = json.loads(result.stdout)
            disks = [item for item in data.get("blockdevices", []) if item.get("type") == "disk"]
        except (subprocess.SubprocessError, json.JSONDecodeError, RuntimeError, OSError) as exc:
            self.disk_count_label.set_text(self.t("lsblk_failed", error=str(exc)))
            self.content.show_all()
            return

        self.disk_count_label.set_text(self.t("disk_count", count=len(disks)))
        if not disks:
            empty = Gtk.Label(label=self.t("empty_disks"))
            empty.set_xalign(0)
            empty.set_margin_top(8)
            empty.set_margin_bottom(8)
            self.disk_list_box.add(empty)
        else:
            for disk in disks:
                row = Gtk.ListBoxRow()
                self.disk_data_by_row[row] = disk
                row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                row_box.set_border_width(12)
                top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                title = Gtk.Label()
                label = disk.get("label") or disk.get("model") or disk.get("name") or self.t("unknown")
                path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
                title.set_markup(f'<span weight="bold">{GLibMarkup.escape(str(label))}</span>')
                title.set_xalign(0)
                top.pack_start(title, True, True, 0)
                badge = Gtk.Label(label=format_bytes(disk.get("size")))
                badge.get_style_context().add_class("status")
                top.pack_start(badge, False, False, 0)
                details = Gtk.Label(label=f"{path}  ·  {disk.get('tran') or self.t('not_available')}  ·  {self.t('disk_removable', value=self.t('yes') if disk.get('rm') else self.t('no'))}")
                details.set_xalign(0)
                details.get_style_context().add_class("muted")
                row_box.pack_start(top, False, False, 0)
                row_box.pack_start(details, False, False, 0)
                row.add(row_box)
                self.disk_list_box.add(row)
        self.disk_list_box.show_all()
        self.content.show_all()

    def on_disk_selected(self, _list_box, row):
        if row is None or self.disk_detail_box is None:
            return
        for child in self.disk_detail_box.get_children():
            self.disk_detail_box.remove(child)
        disk = self.disk_data_by_row.get(row)
        if not disk:
            self.disk_detail_box.show_all()
            return
        label = disk.get("label") or disk.get("model") or disk.get("name") or self.t("unknown")
        path = disk.get("path") or ("/dev/" + str(disk.get("name", "unknown")))
        model = disk.get("model") or self.t("not_available")
        tran = disk.get("tran") or self.t("not_available")
        rm = self.t("yes") if disk.get("rm") else self.t("no")
        ro_value = disk.get("ro")
        if ro_value in (0, "0", False):
            ro_text = self.t("ro_no")
        elif ro_value in (1, "1", True):
            ro_text = self.t("ro_yes")
        else:
            ro_text = self.t("ro_unknown")

        self.disk_detail_box.pack_start(self.make_card(
            str(label),
            "\n".join([
                self.t("disk_device", value=path),
                self.t("disk_size", value=format_bytes(disk.get("size"))),
                self.t("disk_model", value=model),
                self.t("disk_transport", value=tran),
                self.t("disk_removable", value=rm),
                self.t("device_ro", value=ro_text),
            ]),
        ), False, False, 0)

        partitions = disk.get("children") or []
        part_lines = []
        for part in partitions:
            part_path = part.get("path") or ("/dev/" + str(part.get("name", "unknown")))
            part_size = format_bytes(part.get("size"))
            fs = part.get("fstype") or self.t("unknown")
            part_label = part.get("label") or self.t("unknown")
            mount = part.get("mountpoint") or self.t("no")
            part_lines.append(self.t("partition_line", path=part_path, size=part_size, fs=fs, label=part_label, mount=mount))
        if not part_lines:
            part_lines = [self.t("no_partitions")]
        self.disk_detail_box.pack_start(self.make_card(self.t("partition_heading"), "\n".join(part_lines)), False, False, 0)
        safety = Gtk.Label(label=self.t("safety_ro_note"))
        safety.set_xalign(0)
        safety.set_line_wrap(True)
        safety.get_style_context().add_class("muted")
        self.disk_detail_box.pack_start(safety, False, False, 0)
        self.disk_detail_box.show_all()

    def apply_css(self):
        css = b"""
        window { background: #f4f6f9; color: #182230; }
        .sidebar { background: #172435; color: #ffffff; }
        .sidebar label { color: #ffffff; }
        .sidebar button { color: #e6edf5; background: transparent; border-radius: 8px; padding: 10px 12px; }
        .sidebar button:hover { background: #2b3d52; }
        .sidebar button.lang-btn { background: #24354d; border: 1px solid #3a506b; font-weight: bold; }
        .sidebar button.lang-btn:hover { background: #324866; }
        .card { background: #ffffff; border: 1px solid #dce3eb; border-radius: 12px; }
        .card label { color: #182230; }
        .disk-list { background: transparent; }
        .disk-list row { background: #ffffff; border: 1px solid #dce3eb; border-radius: 10px; margin: 4px 0; }
        .disk-list row:selected { background: #e5effb; color: #182230; }
        .muted { color: #667085; }
        .status { color: #245c43; background: #e6f4ec; border-radius: 8px; padding: 5px 8px; }
        button.suggested-action { padding: 10px 16px; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class GLibMarkup:
    """Tiny markup escape helper so device labels cannot inject GTK markup."""
    @staticmethod
    def escape(text):
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("'", "&apos;")
                    .replace('"', "&quot;"))


def main():
    window = RescueOSWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

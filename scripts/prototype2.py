#!/usr/bin/env python3
# Rescue-OS GUI Prototype v0.2 (Bilingual EN/TH)
# Python 3 + GTK 3 (PyGObject)
#
# This is a UI prototype only:
# - Uses mock disk data.
# - Does not mount, modify, or write to any disk.
# - Does not call Rescue-Drive.sh yet.

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


APP_NAME = "Rescue-OS"
APP_VERSION = "Prototype v0.2"

STRINGS = {
    "en": {
        "subtitle_brand": "Recovery environment",
        "nav_dashboard": "Dashboard",
        "nav_dashboard_tip": "Overview",
        "nav_recovery": "Recovery",
        "nav_recovery_tip": "Disk recovery",
        "nav_tools": "Tools",
        "nav_tools_tip": "System tools",
        "nav_about": "About",
        "nav_about_tip": "About this prototype",
        "lang_btn": "🌐 ภาษาไทย (TH)",
        "proto_note": "PROTOTYPE MODE\nNo disks are modified.",
        # Dashboard
        "dash_title": "Dashboard",
        "dash_sub": "Welcome to Rescue-OS. Review the environment before starting recovery.",
        "card_sys_title": "System",
        "card_sys_body": "Alpine Linux / XFCE",
        "card_sys_status": "Demo status",
        "card_stor_title": "Storage",
        "card_stor_body": "2 example devices",
        "card_stor_status": "Mock data only",
        "card_safe_title": "Safety",
        "card_safe_body": "Source disks are not touched",
        "card_safe_status": "UI prototype",
        "card_begin_title": "Before you begin",
        "card_begin_body": (
            "This prototype does not perform recovery yet. "
            "Disk detection, read-only verification, and backup actions "
            "will be connected only after the interface is tested."
        ),
        "btn_open_recovery": "Open Recovery",
        # Recovery
        "rec_title": "Recovery",
        "rec_sub": "Select a source device in a future version. The devices below are examples only.",
        "rec_safe_title": "Safety check",
        "rec_safe_body": "No real disks are scanned or mounted in this prototype.",
        "rec_safe_status": "Not connected to the backend",
        "disk1_name": "Example Disk 1",
        "disk2_name": "Example Disk 2",
        "disk_example_status": "Example only",
        "rec_note": "Next step: connect safe disk discovery and verified read-only checks.",
        # Tools
        "tools_title": "System tools",
        "tools_sub": "Tool integrations will be added after the GUI structure is stable.",
        "tool_smart_title": "S.M.A.R.T. status",
        "tool_smart_body": "Not connected yet. No drive health commands are run.",
        "tool_av_title": "Antivirus scan (ClamAV)",
        "tool_av_body": "Not connected yet. No files are scanned.",
        "tool_eject_title": "Safe eject",
        "tool_eject_body": "Not connected yet. No devices can be ejected from this screen.",
        "tool_unavail": "Unavailable in prototype",
        # About
        "about_title": "About Rescue-OS",
        "about_sub": "A recovery environment focused on understandable workflows and protecting source data.",
        "about_build_title": "Current build",
        "about_build_status": "Interface demo only",
        "about_prin_title": "Design principles",
        "about_prin_body": (
            "1. Make the next step clear.\n"
            "2. Explain risks before actions.\n"
            "3. Verify read-only status in the backend, not just in the UI.\n"
            "4. Never claim a recovery action succeeded until the backend confirms it."
        ),
    },
    "th": {
        "subtitle_brand": "ระบบกู้คืนข้อมูลฉุกเฉิน",
        "nav_dashboard": "หน้าหลัก (Dashboard)",
        "nav_dashboard_tip": "ภาพรวมระบบ",
        "nav_recovery": "กู้ข้อมูล (Recovery)",
        "nav_recovery_tip": "กู้คืนไฟล์จากดิสก์",
        "nav_tools": "เครื่องมือ (Tools)",
        "nav_tools_tip": "เครื่องมือตรวจสอบระบบ",
        "nav_about": "เกี่ยวกับ (About)",
        "nav_about_tip": "ข้อมูลเกี่ยวกับรุ่นทดสอบนี้",
        "lang_btn": "🌐 English (EN)",
        "proto_note": "โหมดต้นแบบ (PROTOTYPE)\nไม่มีการเขียนหรือแก้ไขดิสก์ใดๆ",
        # Dashboard
        "dash_title": "หน้าหลัก (Dashboard)",
        "dash_sub": "ยินดีต้อนรับสู่ Rescue-OS ตรวจสอบสถานะแวดล้อมก่อนเริ่มกู้คืนข้อมูล",
        "card_sys_title": "ระบบปฏิบัติการ (System)",
        "card_sys_body": "Alpine Linux / XFCE",
        "card_sys_status": "สถานะจำลอง (Demo)",
        "card_stor_title": "พื้นที่จัดเก็บ (Storage)",
        "card_stor_body": "อุปกรณ์ตัวอย่าง 2 รายการ",
        "card_stor_status": "ข้อมูลจำลอง (Mock data)",
        "card_safe_title": "ความปลอดภัย (Safety)",
        "card_safe_body": "ไม่แตะต้องดิสก์ต้นฉบับ",
        "card_safe_status": "ต้นแบบ UI (Prototype)",
        "card_begin_title": "ก่อนเริ่มต้นใช้งาน",
        "card_begin_body": (
            "รุ่นต้นแบบนี้ยังไม่ได้เชื่อมต่อคำสั่งกู้ข้อมูลจริง "
            "การตรวจจับดิสก์ การล็อกโหมดอ่านอย่างเดียว (Read-Only) และการสำรองข้อมูล "
            "จะถูกเชื่อมต่อหลังจากทดสอบหน้าตาโปรแกรมเสร็จสิ้น"
        ),
        "btn_open_recovery": "ไปยังหน้ากู้ข้อมูล (Open Recovery)",
        # Recovery
        "rec_title": "กู้คืนข้อมูล (Recovery)",
        "rec_sub": "เลือกดิสก์ต้นทาง (รายการด้านล่างเป็นเพียงข้อมูลตัวอย่างสำหรับการออกแบบ)",
        "rec_safe_title": "การตรวจสอบความปลอดภัย (Safety Check)",
        "rec_safe_body": "ยังไม่มีการสแกนหรือสั่ง Mount ดิสก์จริงในรุ่นต้นแบบนี้",
        "rec_safe_status": "ยังไม่เชื่อมต่อระบบหลังบ้าน (Backend)",
        "disk1_name": "ดิสก์ตัวอย่าง 1 (Example Disk 1)",
        "disk2_name": "ดิสก์ตัวอย่าง 2 (Example Disk 2)",
        "disk_example_status": "ตัวอย่างเท่านั้น (Example)",
        "rec_note": "ขั้นตอนถัดไป: เชื่อมต่อระบบค้นหาพาร์ทิชันและตรวจสอบสถานะ Read-Only ระดับ Kernel",
        # Tools
        "tools_title": "เครื่องมือระบบ (System Tools)",
        "tools_sub": "เครื่องมือเสริมจะถูกเชื่อมต่อหลังจากโครงสร้างหน้าต่าง GUI นิ่งแล้ว",
        "tool_smart_title": "ตรวจสุขภาพดิสก์ (S.M.A.R.T. Status)",
        "tool_smart_body": "ยังไม่ได้เชื่อมต่อ ยังไม่มีการรันคำสั่งตรวจเช็กดิสก์จริง",
        "tool_av_title": "สแกนไวรัส (Antivirus Scan)",
        "tool_av_body": "ยังไม่ได้เชื่อมต่อ ยังไม่มีการสแกนไฟล์จริง",
        "tool_eject_title": "ถอดไดรฟ์ปลอดภัย (Safe Eject)",
        "tool_eject_body": "ยังไม่ได้เชื่อมต่อ ยังไม่สามารถสั่งถอดอุปกรณ์จากหน้านี้ได้",
        "tool_unavail": "ยังไม่เปิดใช้ในรุ่นต้นแบบ",
        # About
        "about_title": "เกี่ยวกับ Rescue-OS",
        "about_sub": "สภาพแวดล้อมสำหรับการกู้ข้อมูลที่เน้นขั้นตอนเข้าใจง่ายและปกป้องข้อมูลต้นฉบับ",
        "about_build_title": "รุ่นปัจจุบัน (Current Build)",
        "about_build_status": "ตัวอย่างหน้าตาโปรแกรม (UI Demo)",
        "about_prin_title": "หลักการออกแบบ (Design Principles)",
        "about_prin_body": (
            "1. แสดงขั้นตอนถัดไปให้ชัดเจนเข้าใจง่าย\n"
            "2. อธิบายความเสี่ยงก่อนเริ่มดำเนินการ\n"
            "3. ยืนยันสถานะ Read-Only ที่ระดับ Kernel หลังบ้าน ไม่ใช่แค่บนหน้าจอ\n"
            "4. ไม่แจ้งว่ากู้ข้อมูลสำเร็จจนกว่าระบบหลังบ้านจะยืนยันผลจริง"
        ),
    },
}


class RescueOSWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=f"{APP_NAME} — {APP_VERSION}")
        self.set_default_size(920, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self.lang = "en"
        self.current_page = "Dashboard"
        self.nav_buttons = {}

        # Main layout: sidebar on the left, scrollable content on the right.
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)

        sidebar = self.build_sidebar()
        root.pack_start(sidebar, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.pack_start(scroller, True, True, 0)

        self.content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        self.content.set_border_width(28)
        scroller.add(self.content)

        self.apply_css()
        self.refresh_ui()

    def t(self, key):
        return STRINGS[self.lang].get(key, key)

    def build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(230, -1)
        sidebar.set_border_width(18)
        sidebar.get_style_context().add_class("sidebar")

        self.brand_label = Gtk.Label()
        self.brand_label.set_xalign(0)
        self.brand_label.set_margin_bottom(24)
        sidebar.pack_start(self.brand_label, False, False, 0)

        nav_keys = [
            ("Dashboard", "nav_dashboard", "nav_dashboard_tip"),
            ("Recovery", "nav_recovery", "nav_recovery_tip"),
            ("Tools", "nav_tools", "nav_tools_tip"),
            ("About", "nav_about", "nav_about_tip"),
        ]

        for page_id, label_key, tip_key in nav_keys:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_halign(Gtk.Align.FILL)
            button.connect("clicked", self.on_navigation_clicked, page_id)
            sidebar.pack_start(button, False, False, 0)
            self.nav_buttons[page_id] = (button, label_key, tip_key)

        spacer = Gtk.Box()
        sidebar.pack_start(spacer, True, True, 0)

        # Language toggle button
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
        for page_id, (button, label_key, tip_key) in self.nav_buttons.items():
            button.set_label(self.t(label_key))
            button.set_tooltip_text(self.t(tip_key))

        self.lang_button.set_label(self.t("lang_btn"))
        self.safety_note.set_markup(
            f'<span size="small">{self.t("proto_note")}</span>'
        )

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

    def add_page_heading(self, title, subtitle):
        heading = Gtk.Label()
        heading.set_markup(
            f'<span size="xx-large" weight="bold">{title}</span>'
        )
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
            status_label.get_style_context().add_class("status")
            card.pack_start(status_label, False, False, 0)

        return card

    def show_page(self, page_name):
        self.current_page = page_name
        self.clear_content()

        if page_name == "Dashboard":
            self.add_page_heading(self.t("dash_title"), self.t("dash_sub"))

            summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            summary.pack_start(
                self.make_card(
                    self.t("card_sys_title"),
                    self.t("card_sys_body"),
                    self.t("card_sys_status"),
                ),
                True, True, 0
            )
            summary.pack_start(
                self.make_card(
                    self.t("card_stor_title"),
                    self.t("card_stor_body"),
                    self.t("card_stor_status"),
                ),
                True, True, 0
            )
            summary.pack_start(
                self.make_card(
                    self.t("card_safe_title"),
                    self.t("card_safe_body"),
                    self.t("card_safe_status"),
                ),
                True, True, 0
            )
            self.content.pack_start(summary, False, False, 0)

            self.content.pack_start(
                self.make_card(
                    self.t("card_begin_title"),
                    self.t("card_begin_body"),
                ),
                False, False, 0
            )

            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            recovery_button = Gtk.Button(label=self.t("btn_open_recovery"))
            recovery_button.get_style_context().add_class("suggested-action")
            recovery_button.connect(
                "clicked", lambda _button: self.show_page("Recovery")
            )
            actions.pack_start(recovery_button, False, False, 0)
            self.content.pack_start(actions, False, False, 0)

        elif page_name == "Recovery":
            self.add_page_heading(self.t("rec_title"), self.t("rec_sub"))

            self.content.pack_start(
                self.make_card(
                    self.t("rec_safe_title"),
                    self.t("rec_safe_body"),
                    self.t("rec_safe_status"),
                ),
                False, False, 0
            )

            disk_list = Gtk.ListBox()
            disk_list.set_selection_mode(Gtk.SelectionMode.NONE)
            disk_list.get_style_context().add_class("card")

            mock_disks = [
                (self.t("disk1_name"), "/dev/sda", "476 GB", "NTFS", self.t("disk_example_status")),
                (self.t("disk2_name"), "/dev/sdb", "29 GB", "FAT32", self.t("disk_example_status")),
            ]

            for name, device, size, filesystem, status in mock_disks:
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=16,
                )
                row_box.set_border_width(14)

                details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                name_label = Gtk.Label()
                name_label.set_markup(f'<span weight="bold">{name}</span>')
                name_label.set_xalign(0)
                details.pack_start(name_label, False, False, 0)

                meta = Gtk.Label(label=f"{device}  •  {size}  •  {filesystem}")
                meta.set_xalign(0)
                meta.get_style_context().add_class("muted")
                details.pack_start(meta, False, False, 0)

                status_label = Gtk.Label(label=status)
                status_label.get_style_context().add_class("status")

                row_box.pack_start(details, True, True, 0)
                row_box.pack_start(status_label, False, False, 0)
                row.add(row_box)
                disk_list.add(row)

            self.content.pack_start(disk_list, False, False, 0)

            note = Gtk.Label(label=self.t("rec_note"))
            note.set_xalign(0)
            note.set_line_wrap(True)
            note.get_style_context().add_class("muted")
            self.content.pack_start(note, False, False, 0)

        elif page_name == "Tools":
            self.add_page_heading(self.t("tools_title"), self.t("tools_sub"))
            self.content.pack_start(
                self.make_card(
                    self.t("tool_smart_title"),
                    self.t("tool_smart_body"),
                    self.t("tool_unavail"),
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    self.t("tool_av_title"),
                    self.t("tool_av_body"),
                    self.t("tool_unavail"),
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    self.t("tool_eject_title"),
                    self.t("tool_eject_body"),
                    self.t("tool_unavail"),
                ),
                False, False, 0
            )

        elif page_name == "About":
            self.add_page_heading(self.t("about_title"), self.t("about_sub"))
            self.content.pack_start(
                self.make_card(
                    self.t("about_build_title"),
                    f"{APP_NAME} {APP_VERSION}",
                    self.t("about_build_status"),
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    self.t("about_prin_title"),
                    self.t("about_prin_body"),
                ),
                False, False, 0
            )

        self.content.show_all()

    def apply_css(self):
        css = b"""
        window {
            background: #f4f6f9;
            color: #182230;
        }
        .sidebar {
            background: #172435;
            color: #ffffff;
        }
        .sidebar label {
            color: #ffffff;
        }
        .sidebar button {
            color: #e6edf5;
            background: transparent;
            border-radius: 8px;
            padding: 10px 12px;
        }
        .sidebar button:hover {
            background: #2b3d52;
        }
        .sidebar button.lang-btn {
            background: #24354d;
            border: 1px solid #3a506b;
            font-weight: bold;
        }
        .sidebar button.lang-btn:hover {
            background: #324866;
        }
        .card {
            background: #ffffff;
            border: 1px solid #dce3eb;
            border-radius: 12px;
        }
        .card label {
            color: #182230;
        }
        .muted {
            color: #667085;
        }
        .status {
            color: #245c43;
            background: #e6f4ec;
            border-radius: 8px;
            padding: 5px 8px;
        }
        button.suggested-action {
            padding: 10px 16px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def main():
    window = RescueOSWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
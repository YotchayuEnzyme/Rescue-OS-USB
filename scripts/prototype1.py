#!/usr/bin/env python3
# Rescue-OS GUI Prototype v0.1
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
APP_VERSION = "Prototype v0.1"


class RescueOSWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=f"{APP_NAME} — {APP_VERSION}")
        self.set_default_size(1080, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        # Main layout: sidebar on the left, content on the right.
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)

        sidebar = self.build_sidebar()
        root.pack_start(sidebar, False, False, 0)

        self.content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        self.content.set_border_width(28)
        root.pack_start(self.content, True, True, 0)

        self.show_page("Dashboard")
        self.apply_css()

    def build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(220, -1)
        sidebar.set_border_width(18)
        sidebar.get_style_context().add_class("sidebar")

        brand = Gtk.Label()
        brand.set_markup(
            '<span size="large" weight="bold">Rescue-OS</span>\n'
            '<span size="small">Recovery environment</span>'
        )
        brand.set_xalign(0)
        brand.set_margin_bottom(28)
        sidebar.pack_start(brand, False, False, 0)

        nav_items = [
            ("Dashboard", "Overview"),
            ("Recovery", "Disk recovery"),
            ("Tools", "System tools"),
            ("About", "About this prototype"),
        ]

        for page_name, accessible_name in nav_items:
            button = Gtk.Button(label=page_name)
            button.set_tooltip_text(accessible_name)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_halign(Gtk.Align.FILL)
            button.connect("clicked", self.on_navigation_clicked, page_name)
            sidebar.pack_start(button, False, False, 0)

        spacer = Gtk.Box()
        sidebar.pack_start(spacer, True, True, 0)

        safety_note = Gtk.Label()
        safety_note.set_markup(
            '<span size="small">PROTOTYPE MODE\n'
            'No disks are modified.</span>'
        )
        safety_note.set_xalign(0)
        safety_note.set_line_wrap(True)
        sidebar.pack_start(safety_note, False, False, 0)

        return sidebar

    def on_navigation_clicked(self, _button, page_name):
        self.show_page(page_name)

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
        self.clear_content()

        if page_name == "Dashboard":
            self.add_page_heading(
                "Dashboard",
                "Welcome to Rescue-OS. Review the environment before starting recovery.",
            )

            summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            summary.pack_start(
                self.make_card("System", "Alpine Linux / XFCE", "Demo status"),
                True, True, 0
            )
            summary.pack_start(
                self.make_card("Storage", "2 example devices", "Mock data only"),
                True, True, 0
            )
            summary.pack_start(
                self.make_card("Safety", "Source disks are not touched", "UI prototype"),
                True, True, 0
            )
            self.content.pack_start(summary, False, False, 0)

            self.content.pack_start(
                self.make_card(
                    "Before you begin",
                    "This prototype does not perform recovery yet. "
                    "Disk detection, read-only verification, and backup actions "
                    "will be connected only after the interface is tested.",
                ),
                False, False, 0
            )

            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            recovery_button = Gtk.Button(label="Open Recovery")
            recovery_button.get_style_context().add_class("suggested-action")
            recovery_button.connect(
                "clicked", lambda _button: self.show_page("Recovery")
            )
            actions.pack_start(recovery_button, False, False, 0)
            self.content.pack_start(actions, False, False, 0)

        elif page_name == "Recovery":
            self.add_page_heading(
                "Recovery",
                "Select a source device in a future version. The devices below are examples only.",
            )

            self.content.pack_start(
                self.make_card(
                    "Safety check",
                    "No real disks are scanned or mounted in this prototype.",
                    "Not connected to the backend",
                ),
                False, False, 0
            )

            disk_list = Gtk.ListBox()
            disk_list.set_selection_mode(Gtk.SelectionMode.NONE)
            disk_list.get_style_context().add_class("card")

            mock_disks = [
                ("Example Disk 1", "/dev/sda", "476 GB", "NTFS", "Example only"),
                ("Example Disk 2", "/dev/sdb", "29 GB", "FAT32", "Example only"),
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

            note = Gtk.Label(
                label="Next step: connect safe disk discovery and verified read-only checks."
            )
            note.set_xalign(0)
            note.set_line_wrap(True)
            note.get_style_context().add_class("muted")
            self.content.pack_start(note, False, False, 0)

        elif page_name == "Tools":
            self.add_page_heading(
                "System tools",
                "Tool integrations will be added after the GUI structure is stable.",
            )
            self.content.pack_start(
                self.make_card(
                    "SMART status",
                    "Not connected yet. No drive health commands are run.",
                    "Unavailable in prototype",
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    "Antivirus scan",
                    "Not connected yet. No files are scanned.",
                    "Unavailable in prototype",
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    "Safe eject",
                    "Not connected yet. No devices can be ejected from this screen.",
                    "Unavailable in prototype",
                ),
                False, False, 0
            )

        elif page_name == "About":
            self.add_page_heading(
                "About Rescue-OS",
                "A recovery environment focused on understandable workflows and protecting source data.",
            )
            self.content.pack_start(
                self.make_card(
                    "Current build",
                    f"{APP_NAME} {APP_VERSION}",
                    "Interface demo only",
                ),
                False, False, 0
            )
            self.content.pack_start(
                self.make_card(
                    "Design principles",
                    "1. Make the next step clear.\n"
                    "2. Explain risks before actions.\n"
                    "3. Verify read-only status in the backend, not just in the UI.\n"
                    "4. Never claim a recovery action succeeded until the backend confirms it.",
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
        .card {
            background: #ffffff;
            border: 1px solid #dce3eb;
            border-radius: 12px;
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

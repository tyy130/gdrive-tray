#!/usr/bin/env python3
"""
gdrive-tray — system tray wrapper for rclone gdrive mount.
Color icon = mounted, greyscale = unmounted.
Double-click (or middle-click) the icon to open the folder.
"""

import subprocess
import threading
import os
import sys
import tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, AppIndicator3, GLib, Notify

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Missing dependency: pip install pillow numpy")
    sys.exit(1)

APP_ID      = "com.tacticdev.gdrive-tray"
APP_NAME    = "GDrive"
SCRIPT_DIR  = Path(__file__).parent
ICON_SRC    = SCRIPT_DIR / "gdrive-icon.png"
REMOTE      = "gdrive:"
MOUNT_POINT = Path("/home/tyler/CloudDrive")

# Build PNG temp files for mounted/unmounted states at startup
def _build_icons():
    arr = np.array(Image.open(ICON_SRC).convert("RGBA"), dtype=np.uint8)

    color = Image.fromarray(arr, "RGBA").resize((64, 64), Image.LANCZOS)

    grey = arr.copy()
    lum = (0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]).astype(np.uint8)
    grey[:,:,0] = grey[:,:,1] = grey[:,:,2] = lum
    grey_img = Image.fromarray(grey, "RGBA").resize((64, 64), Image.LANCZOS)

    # Write to stable temp paths (AppIndicator needs a file path)
    color_path = "/tmp/gdrive-icon-color.png"
    grey_path  = "/tmp/gdrive-icon-grey.png"
    color.save(color_path)
    grey_img.save(grey_path)
    return color_path, grey_path

ICON_COLOR, ICON_GREY = _build_icons()


def is_mounted() -> bool:
    return subprocess.run(
        ["findmnt", "--mountpoint", str(MOUNT_POINT)],
        capture_output=True,
    ).returncode == 0


class GDriveTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_COLOR,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title(APP_NAME)

        Notify.init(APP_NAME)
        self._build_menu()
        self._refresh()

    def _build_menu(self):
        self.menu = Gtk.Menu()

        self.status_item = Gtk.MenuItem(label="Checking…")
        self.status_item.set_sensitive(False)
        self.menu.append(self.status_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.mount_item = Gtk.MenuItem(label="Mount")
        self.mount_item.connect("activate", self._on_mount)
        self.menu.append(self.mount_item)

        self.unmount_item = Gtk.MenuItem(label="Unmount")
        self.unmount_item.connect("activate", self._on_unmount)
        self.menu.append(self.unmount_item)

        self.open_item = Gtk.MenuItem(label="Open Folder")
        self.open_item.connect("activate", self._on_open)
        self.menu.append(self.open_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Double-click / middle-click the tray icon → open folder
        self.indicator.set_secondary_activate_target(self.open_item)

    def _refresh(self):
        mounted = is_mounted()
        GLib.idle_add(self._apply_state, mounted)

    def _apply_state(self, mounted):
        self.indicator.set_icon_full(
            ICON_COLOR if mounted else ICON_GREY,
            "Mounted" if mounted else "Unmounted",
        )
        self.status_item.set_label("● Mounted" if mounted else "○ Not mounted")
        self.mount_item.set_sensitive(not mounted)
        self.unmount_item.set_sensitive(mounted)
        self.open_item.set_sensitive(mounted)

    def _notify(self, title, body):
        n = Notify.Notification.new(title, body, "drive-harddisk")
        n.set_timeout(2000)
        n.show()

    def _on_open(self, _):
        if not is_mounted():
            GLib.idle_add(self._notify, "GDrive", "Not mounted — mount first")
            return
        subprocess.Popen(["xdg-open", str(MOUNT_POINT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _on_mount(self, _):
        threading.Thread(target=self._do_mount, daemon=True).start()

    def _do_mount(self):
        MOUNT_POINT.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["rclone", "mount", REMOTE, str(MOUNT_POINT),
             "--daemon", "--vfs-cache-mode", "writes",
             "--dir-cache-time", "5m", "--log-level", "ERROR"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            GLib.idle_add(self._notify, "GDrive", "Mounted successfully")
        else:
            GLib.idle_add(self._notify, "GDrive Error", r.stderr.strip() or "Mount failed")
        self._refresh()

    def _on_unmount(self, _):
        threading.Thread(target=self._do_unmount, daemon=True).start()

    def _do_unmount(self):
        r = subprocess.run(["fusermount", "-u", str(MOUNT_POINT)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            subprocess.run(["fusermount", "-uz", str(MOUNT_POINT)], capture_output=True)
        GLib.idle_add(self._notify, "GDrive", "Unmounted")
        self._refresh()

    def run(self):
        Gtk.main()


if __name__ == "__main__":
    GDriveTray().run()

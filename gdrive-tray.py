#!/usr/bin/env python3
"""
gdrive-tray — system tray wrapper for rclone gdrive mount.
Green icon = mounted, grey icon = unmounted.
"""

import subprocess
import threading
import os
import sys
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"Missing dependency: {e}\nRun: pip install pystray pillow --break-system-packages")
    sys.exit(1)

REMOTE = "gdrive:"
MOUNT_POINT = Path("/home/tyler/CloudDrive")
ICON_PATH = Path(__file__).parent / "gdrive-icon.png"

# Pre-load and cache the icon variants at startup
def _load_icon_variants():
    import numpy as np
    arr = np.array(Image.open(ICON_PATH).convert("RGBA"), dtype=np.uint8)

    color_img = Image.fromarray(arr, "RGBA").resize((64, 64), Image.LANCZOS)

    # Greyscale variant for unmounted state (preserve alpha)
    grey_arr = arr.copy()
    luminance = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.uint8)
    grey_arr[:, :, 0] = luminance
    grey_arr[:, :, 1] = luminance
    grey_arr[:, :, 2] = luminance
    grey_img = Image.fromarray(grey_arr, "RGBA").resize((64, 64), Image.LANCZOS)

    return color_img, grey_img

try:
    _ICON_COLOR, _ICON_GREY = _load_icon_variants()
except Exception as e:
    print(f"Warning: could not load gdrive-icon.png ({e}), falling back to drawn icon")
    _ICON_COLOR = _ICON_GREY = None


def is_mounted() -> bool:
    result = subprocess.run(
        ["findmnt", "--mountpoint", str(MOUNT_POINT)],
        capture_output=True,
    )
    return result.returncode == 0


def make_icon(mounted: bool) -> Image.Image:
    if _ICON_COLOR is not None:
        return _ICON_COLOR if mounted else _ICON_GREY

    # Fallback: drawn icon
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (40, 200, 80, 255) if mounted else (120, 120, 120, 255)
    draw.ellipse([8, 20, 36, 46], fill=color)
    draw.ellipse([24, 14, 56, 44], fill=color)
    draw.rectangle([8, 32, 56, 50], fill=color)
    draw.ellipse([26, 34, 38, 46], fill=(255, 255, 255, 200))
    return img


def notify(title: str, message: str):
    subprocess.Popen(
        ["notify-send", "-a", "GDrive Tray", title, message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def mount(icon, item):
    if is_mounted():
        notify("GDrive", "Already mounted")
        return
    threading.Thread(target=_do_mount, args=(icon,), daemon=True).start()


def _do_mount(icon):
    MOUNT_POINT.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "rclone", "mount", REMOTE, str(MOUNT_POINT),
            "--daemon",
            "--vfs-cache-mode", "writes",
            "--dir-cache-time", "5m",
            "--log-level", "ERROR",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        notify("GDrive", "Mounted successfully")
    else:
        notify("GDrive Error", result.stderr.strip() or "Mount failed")
    refresh_icon(icon)


def unmount(icon, item):
    if not is_mounted():
        notify("GDrive", "Not mounted")
        return
    threading.Thread(target=_do_unmount, args=(icon,), daemon=True).start()


def _do_unmount(icon):
    result = subprocess.run(
        ["fusermount", "-u", str(MOUNT_POINT)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        notify("GDrive", "Unmounted")
    else:
        # Try lazy unmount as fallback
        subprocess.run(["fusermount", "-uz", str(MOUNT_POINT)], capture_output=True)
        notify("GDrive", "Unmounted (lazy)")
    refresh_icon(icon)


def open_folder(icon, item):
    if not is_mounted():
        notify("GDrive", "Not mounted — mount first")
        return
    subprocess.Popen(
        ["xdg-open", str(MOUNT_POINT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def refresh_icon(icon):
    mounted = is_mounted()
    icon.icon = make_icon(mounted)
    status = "Mounted" if mounted else "Unmounted"
    icon.title = f"GDrive — {status}"
    icon.menu = build_menu(icon, mounted)


def build_menu(icon, mounted: bool):
    status_label = "● Mounted" if mounted else "○ Not mounted"
    return pystray.Menu(
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Mount", mount, enabled=not mounted),
        pystray.MenuItem("Unmount", unmount, enabled=mounted),
        pystray.MenuItem("Open folder", open_folder, enabled=mounted, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )


def main():
    mounted = is_mounted()
    icon = pystray.Icon(
        name="gdrive-tray",
        icon=make_icon(mounted),
        title=f"GDrive — {'Mounted' if mounted else 'Unmounted'}",
        menu=build_menu(None, mounted),
    )
    # Fix circular ref: build_menu needs icon for refresh, so rebuild with real icon
    icon.menu = build_menu(icon, mounted)
    icon.run()


if __name__ == "__main__":
    main()

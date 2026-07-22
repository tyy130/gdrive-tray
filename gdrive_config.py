"""Environment-backed configuration for gdrive-tray."""

import os
from pathlib import Path
from typing import Mapping


def get_remote(environment: Mapping[str, str] | None = None) -> str:
    """Return the configured rclone remote, including its trailing colon."""
    values = os.environ if environment is None else environment
    return values.get("GDRIVE_REMOTE", "gdrive:")


def get_mount_point(environment: Mapping[str, str] | None = None) -> Path:
    """Return the configured mount point with user-home expansion applied."""
    values = os.environ if environment is None else environment
    return Path(values.get("GDRIVE_MOUNT_POINT", "~/CloudDrive")).expanduser()

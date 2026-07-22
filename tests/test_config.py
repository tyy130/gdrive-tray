from pathlib import Path

from gdrive_config import get_mount_point, get_remote


def test_default_remote():
    assert get_remote({}) == "gdrive:"


def test_remote_can_be_overridden():
    assert get_remote({"GDRIVE_REMOTE": "work-drive:"}) == "work-drive:"


def test_default_mount_point_uses_current_home(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp/test-user")
    assert get_mount_point({}) == Path("/tmp/test-user/CloudDrive")


def test_mount_point_can_be_overridden():
    assert get_mount_point({"GDRIVE_MOUNT_POINT": "/mnt/google"}) == Path("/mnt/google")

"""Shared path utilities for unit file installation."""

from __future__ import annotations

from pathlib import Path

from systemd_client.enums import SystemdScope


def unit_file_dir(scope: SystemdScope) -> Path:
    """Return the directory for installing unit files based on scope."""
    if scope == SystemdScope.SYSTEM:
        return Path("/etc/systemd/system")
    return Path.home() / ".config" / "systemd" / "user"

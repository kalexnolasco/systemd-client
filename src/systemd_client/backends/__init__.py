"""Backend factory and re-exports."""

from __future__ import annotations

from systemd_client.backends._base import AbstractBackend
from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.enums import BackendType
from systemd_client.exceptions import BackendNotAvailableError

__all__ = [
    "AbstractBackend",
    "BackendType",
    "SubprocessBackend",
    "get_backend",
]


def get_backend(backend_type: BackendType = BackendType.AUTO) -> AbstractBackend:
    """Create and return the appropriate backend instance."""
    if backend_type == BackendType.SUBPROCESS:
        return SubprocessBackend()

    if backend_type == BackendType.DBUS:
        try:
            from systemd_client.backends._dbus import DBusBackend
            return DBusBackend()
        except ImportError as exc:
            raise BackendNotAvailableError(
                "dbus",
                "dasbus is not installed. Install with: pip install systemd-client[dbus]",
            ) from exc

    # AUTO: try dbus first, fall back to subprocess
    try:
        from systemd_client.backends._dbus import DBusBackend
        return DBusBackend()
    except (ImportError, Exception):
        return SubprocessBackend()

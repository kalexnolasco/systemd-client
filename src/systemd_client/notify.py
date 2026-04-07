"""sd_notify protocol — notify systemd about service state from Python.

Pure Python implementation, zero dependencies. Sends datagrams to
the $NOTIFY_SOCKET unix socket.

Usage from a Type=notify service:

    from systemd_client.notify import SystemdNotifier

    notifier = SystemdNotifier()
    notifier.ready()
    notifier.status("Listening on :8080")
    # ... in a loop:
    notifier.watchdog()
"""

from __future__ import annotations

import os
import socket


class SystemdNotifier:
    """Send sd_notify(3) messages to systemd."""

    def __init__(self) -> None:
        self._socket_path = os.environ.get("NOTIFY_SOCKET", "")
        self._sock: socket.socket | None = None

    @property
    def available(self) -> bool:
        """Whether $NOTIFY_SOCKET is set (i.e., running under systemd Type=notify)."""
        return bool(self._socket_path)

    def notify(self, state: str) -> bool:
        """Send a raw notification string. Returns True if sent, False otherwise."""
        if not self._socket_path:
            return False
        try:
            if self._sock is None:
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            addr = self._socket_path
            if addr.startswith("@"):
                addr = "\0" + addr[1:]
            self._sock.sendto(state.encode("utf-8"), addr)
        except OSError:
            return False
        return True

    def ready(self) -> bool:
        """Notify systemd that the service is ready (READY=1)."""
        return self.notify("READY=1")

    def status(self, text: str) -> bool:
        """Update the service status text."""
        return self.notify(f"STATUS={text}")

    def stopping(self) -> bool:
        """Notify systemd that the service is stopping."""
        return self.notify("STOPPING=1")

    def reloading(self) -> bool:
        """Notify systemd that the service is reloading configuration."""
        return self.notify("RELOADING=1")

    def watchdog(self) -> bool:
        """Send watchdog keep-alive ping."""
        return self.notify("WATCHDOG=1")

    def errno(self, n: int) -> bool:
        """Report an error number."""
        return self.notify(f"ERRNO={n}")

    def mainpid(self, pid: int) -> bool:
        """Report the main PID."""
        return self.notify(f"MAINPID={pid}")

    def extend_timeout(self, usec: int) -> bool:
        """Request an extension of the startup/shutdown timeout."""
        return self.notify(f"EXTEND_TIMEOUT_USEC={usec}")

    def close(self) -> None:
        """Close the notification socket."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

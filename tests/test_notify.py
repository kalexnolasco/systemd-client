"""Tests for sd_notify module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from systemd_client.notify import SystemdNotifier


class TestSystemdNotifier:
    def test_not_available_without_socket(self):
        with patch.dict(os.environ, {}, clear=True):
            n = SystemdNotifier()
            assert n.available is False
            assert n.ready() is False

    def test_available_with_socket(self, tmp_path):
        sock_path = str(tmp_path / "notify.sock")
        with patch.dict(os.environ, {"NOTIFY_SOCKET": sock_path}):
            n = SystemdNotifier()
            assert n.available is True

    def test_ready(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        assert n.ready() is True
        n._sock.sendto.assert_called_once_with(b"READY=1", "/tmp/test.sock")

    def test_status(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.status("Processing requests")
        n._sock.sendto.assert_called_once_with(
            b"STATUS=Processing requests", "/tmp/test.sock",
        )

    def test_stopping(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.stopping()
        n._sock.sendto.assert_called_once_with(b"STOPPING=1", "/tmp/test.sock")

    def test_reloading(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.reloading()
        n._sock.sendto.assert_called_once_with(b"RELOADING=1", "/tmp/test.sock")

    def test_watchdog(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.watchdog()
        n._sock.sendto.assert_called_once_with(b"WATCHDOG=1", "/tmp/test.sock")

    def test_errno(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.errno(22)
        n._sock.sendto.assert_called_once_with(b"ERRNO=22", "/tmp/test.sock")

    def test_mainpid(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.mainpid(12345)
        n._sock.sendto.assert_called_once_with(b"MAINPID=12345", "/tmp/test.sock")

    def test_extend_timeout(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n.extend_timeout(5000000)
        n._sock.sendto.assert_called_once_with(
            b"EXTEND_TIMEOUT_USEC=5000000", "/tmp/test.sock",
        )

    def test_abstract_socket(self):
        n = SystemdNotifier()
        n._socket_path = "@/run/notify"
        n._sock = MagicMock()
        n.ready()
        n._sock.sendto.assert_called_once_with(b"READY=1", "\0/run/notify")

    def test_close(self):
        n = SystemdNotifier()
        mock_sock = MagicMock()
        n._sock = mock_sock
        n.close()
        mock_sock.close.assert_called_once()
        assert n._sock is None

    def test_oserror_returns_false(self):
        n = SystemdNotifier()
        n._socket_path = "/tmp/test.sock"
        n._sock = MagicMock()
        n._sock.sendto.side_effect = OSError("Connection refused")
        assert n.notify("READY=1") is False

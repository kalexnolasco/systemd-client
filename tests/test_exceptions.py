"""Tests for exception hierarchy."""

import pytest

from systemd_client.exceptions import (
    BackendError,
    BackendNotAvailableError,
    JournalError,
    JournalParseError,
    SubprocessError,
    SystemdClientError,
    UnitNotFoundError,
    UnitOperationError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        assert issubclass(UnitNotFoundError, SystemdClientError)
        assert issubclass(UnitOperationError, SystemdClientError)
        assert issubclass(BackendError, SystemdClientError)
        assert issubclass(BackendNotAvailableError, BackendError)
        assert issubclass(SubprocessError, BackendError)
        assert issubclass(JournalError, SystemdClientError)
        assert issubclass(JournalParseError, JournalError)


class TestUnitNotFoundError:
    def test_message(self):
        exc = UnitNotFoundError("foo.service")
        assert exc.unit_name == "foo.service"
        assert "foo.service" in str(exc)


class TestUnitOperationError:
    def test_message(self):
        exc = UnitOperationError("foo.service", "start", "permission denied")
        assert exc.unit_name == "foo.service"
        assert exc.operation == "start"
        assert "permission denied" in str(exc)


class TestSubprocessError:
    def test_message(self):
        exc = SubprocessError(["systemctl", "--user", "start", "foo"], 1, "not found")
        assert exc.returncode == 1
        assert exc.stderr == "not found"
        assert "exit code 1" in str(exc)


class TestBackendNotAvailableError:
    def test_message(self):
        exc = BackendNotAvailableError("dbus", "dasbus not installed")
        assert exc.backend == "dbus"
        assert "dasbus not installed" in str(exc)


class TestJournalParseError:
    def test_with_detail(self):
        exc = JournalParseError("bad json")
        assert "bad json" in str(exc)

    def test_without_detail(self):
        exc = JournalParseError()
        assert "parse journal" in str(exc).lower()

"""Tests for enums module."""

from systemd_client.enums import (
    ActiveState,
    BackendType,
    JournalPriority,
    LoadState,
    SubState,
    SystemdScope,
    UnitFileState,
    UnitType,
)


class TestActiveState:
    def test_values(self):
        assert ActiveState.ACTIVE == "active"
        assert ActiveState.FAILED == "failed"
        assert ActiveState("inactive") == ActiveState.INACTIVE

    def test_is_str(self):
        assert isinstance(ActiveState.ACTIVE, str)
        assert f"state={ActiveState.ACTIVE}" == "state=active"


class TestLoadState:
    def test_values(self):
        assert LoadState.LOADED == "loaded"
        assert LoadState.NOT_FOUND == "not-found"
        assert LoadState.MASKED == "masked"


class TestUnitFileState:
    def test_all_values_exist(self):
        assert len(UnitFileState) == 13
        assert UnitFileState.ENABLED_RUNTIME == "enabled-runtime"

    def test_from_string(self):
        assert UnitFileState("static") == UnitFileState.STATIC


class TestSubState:
    def test_running(self):
        assert SubState.RUNNING == "running"
        assert SubState.DEAD == "dead"


class TestUnitType:
    def test_service(self):
        assert UnitType.SERVICE == "service"
        assert UnitType.TIMER == "timer"
        assert len(UnitType) == 11


class TestJournalPriority:
    def test_numeric_values(self):
        assert JournalPriority.EMERG == "0"
        assert JournalPriority.DEBUG == "7"
        assert JournalPriority.WARNING == "4"

    def test_ordering(self):
        # Lower value = higher priority
        assert JournalPriority.ERR.value < JournalPriority.WARNING.value


class TestBackendType:
    def test_values(self):
        assert BackendType.AUTO == "auto"
        assert BackendType.SUBPROCESS == "subprocess"
        assert BackendType.DBUS == "dbus"


class TestSystemdScope:
    def test_values(self):
        assert SystemdScope.USER == "user"
        assert SystemdScope.SYSTEM == "system"

    def test_from_string(self):
        assert SystemdScope("user") == SystemdScope.USER
        assert SystemdScope("system") == SystemdScope.SYSTEM

    def test_is_str(self):
        assert isinstance(SystemdScope.USER, str)
        assert f"--{SystemdScope.USER}" == "--user"

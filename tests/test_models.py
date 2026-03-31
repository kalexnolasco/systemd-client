"""Tests for data models."""

from datetime import datetime, timezone

import pytest

from systemd_client.enums import ActiveState, JournalPriority, LoadState, SubState
from systemd_client.models import EnableResult, JournalEntry, UnitInfo, UnitStatus


class TestUnitInfo:
    def test_creation(self):
        info = UnitInfo(
            name="test.service",
            description="Test",
            load_state=LoadState.LOADED,
            active_state=ActiveState.ACTIVE,
            sub_state=SubState.RUNNING,
        )
        assert info.name == "test.service"
        assert info.unit_file_state is None

    def test_frozen(self):
        info = UnitInfo(
            name="test.service",
            description="Test",
            load_state=LoadState.LOADED,
            active_state=ActiveState.ACTIVE,
            sub_state=SubState.RUNNING,
        )
        with pytest.raises(AttributeError):
            info.name = "other"  # type: ignore[misc]


class TestUnitStatus:
    def test_full_creation(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        status = UnitStatus(
            name="test.service",
            description="Test",
            load_state=LoadState.LOADED,
            active_state=ActiveState.ACTIVE,
            sub_state=SubState.RUNNING,
            fragment_path="/etc/systemd/user/test.service",
            active_enter_timestamp=ts,
            main_pid=1234,
            properties={"key": "value"},
        )
        assert status.main_pid == 1234
        assert status.properties["key"] == "value"

    def test_defaults(self):
        status = UnitStatus(
            name="test.service",
            description="",
            load_state=LoadState.LOADED,
            active_state=ActiveState.INACTIVE,
            sub_state=SubState.DEAD,
        )
        assert status.triggered_by == []
        assert status.documentation == []
        assert status.properties == {}


class TestJournalEntry:
    def test_creation(self):
        entry = JournalEntry(
            message="Hello",
            priority=JournalPriority.INFO,
            pid=123,
        )
        assert entry.message == "Hello"
        assert entry.priority == JournalPriority.INFO
        assert entry.pid == 123
        assert entry.fields == {}


class TestEnableResult:
    def test_defaults(self):
        result = EnableResult()
        assert result.changes == []
        assert result.carries_install_info is False

    def test_with_changes(self):
        result = EnableResult(
            changes=[("Created", "symlink", "/path/to")],
            carries_install_info=True,
        )
        assert len(result.changes) == 1
        assert result.carries_install_info is True

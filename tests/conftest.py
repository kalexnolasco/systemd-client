"""Shared test fixtures and mock factories."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from systemd_client.enums import ActiveState, LoadState, SubState, UnitFileState
from systemd_client.models import UnitFileInfo, UnitInfo


@pytest.fixture
def sample_unit_info() -> UnitInfo:
    """A sample UnitInfo for testing."""
    return UnitInfo(
        name="test-app.service",
        description="Test Application",
        load_state=LoadState.LOADED,
        active_state=ActiveState.ACTIVE,
        sub_state=SubState.RUNNING,
    )


@pytest.fixture
def sample_list_units_json() -> str:
    """Sample JSON output from systemctl list-units --output=json."""
    return json.dumps([
        {
            "unit": "test-app.service",
            "description": "Test Application",
            "load": "loaded",
            "active": "active",
            "sub": "running",
        },
        {
            "unit": "test-timer.timer",
            "description": "Test Timer",
            "load": "loaded",
            "active": "inactive",
            "sub": "dead",
        },
    ])


@pytest.fixture
def sample_list_unit_files_json() -> str:
    """Sample JSON output from systemctl list-unit-files --output=json."""
    return json.dumps([
        {"unit_file": "test-app.service", "state": "enabled", "preset": "enabled"},
        {"unit_file": "test-timer.timer", "state": "disabled", "preset": "disabled"},
        {"unit_file": "test-masked.service", "state": "masked"},
    ])


@pytest.fixture
def sample_show_output() -> str:
    """Sample output from systemctl show."""
    return "\n".join([
        "Id=test-app.service",
        "Description=Test Application",
        "LoadState=loaded",
        "ActiveState=active",
        "SubState=running",
        "UnitFileState=enabled",
        "FragmentPath=/home/user/.config/systemd/user/test-app.service",
        "MainPID=12345",
        "ExecMainStatus=0",
        "Result=success",
        "TriggeredBy=",
        "Documentation=",
    ])


@pytest.fixture
def sample_journal_json_lines() -> list[str]:
    """Sample JSON lines from journalctl --output=json."""
    return [
        json.dumps({
            "MESSAGE": "Application started",
            "PRIORITY": "6",
            "__REALTIME_TIMESTAMP": "1700000000000000",
            "_SYSTEMD_UNIT": "test-app.service",
            "SYSLOG_IDENTIFIER": "test-app",
            "_PID": "12345",
            "_HOSTNAME": "testhost",
            "__CURSOR": "s=abc123",
        }),
        json.dumps({
            "MESSAGE": "Warning: low memory",
            "PRIORITY": "4",
            "__REALTIME_TIMESTAMP": "1700000001000000",
            "_SYSTEMD_UNIT": "test-app.service",
            "SYSLOG_IDENTIFIER": "test-app",
            "_PID": "12345",
            "_HOSTNAME": "testhost",
            "__CURSOR": "s=abc124",
        }),
    ]


@pytest.fixture
def sample_unit_file_info() -> list[UnitFileInfo]:
    """Sample UnitFileInfo list."""
    return [
        UnitFileInfo(name="test-app.service", state=UnitFileState.ENABLED, preset="enabled"),
        UnitFileInfo(name="test-timer.timer", state=UnitFileState.DISABLED, preset="disabled"),
    ]


@pytest.fixture
def mock_subprocess_run(monkeypatch: pytest.MonkeyPatch):
    """Factory for mocking asyncio.create_subprocess_exec."""
    def _factory(stdout: str = "", stderr: str = "", returncode: int = 0):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            return_value=(stdout.encode(), stderr.encode())
        )
        mock_proc.returncode = returncode
        mock_proc.stdout = None
        mock_proc.stderr = None

        mock_create = AsyncMock(return_value=mock_proc)
        monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create)
        return mock_create, mock_proc

    return _factory

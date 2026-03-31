"""Tests for subprocess backend."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.enums import ActiveState, LoadState, SubState
from systemd_client.exceptions import SubprocessError, UnitNotFoundError, UnitOperationError


@pytest.fixture
def backend():
    return SubprocessBackend()


@pytest.fixture
def mock_systemctl(monkeypatch):
    """Helper to mock _run_systemctl on the backend."""
    def _factory(stdout: str = "", stderr: str = "", returncode: int = 0):
        mock = AsyncMock(return_value=(stdout, stderr, returncode))
        monkeypatch.setattr(SubprocessBackend, "_run_systemctl", mock)
        return mock
    return _factory


class TestListUnits:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_systemctl, sample_list_units_json):
        mock_systemctl(stdout=sample_list_units_json)
        units = await backend.list_units()
        assert len(units) == 2
        assert units[0].name == "test-app.service"
        assert units[0].active_state == ActiveState.ACTIVE

    @pytest.mark.asyncio
    async def test_empty_list(self, backend, mock_systemctl):
        mock_systemctl(stdout="[]")
        units = await backend.list_units()
        assert units == []


class TestGetUnitStatus:
    @pytest.mark.asyncio
    async def test_parses_show_output(self, backend, mock_systemctl, sample_show_output):
        mock_systemctl(stdout=sample_show_output)
        status = await backend.get_unit_status("test-app.service")
        assert status.name == "test-app.service"
        assert status.active_state == ActiveState.ACTIVE
        assert status.load_state == LoadState.LOADED
        assert status.main_pid == 12345

    @pytest.mark.asyncio
    async def test_not_found(self, backend, mock_systemctl):
        mock_systemctl(stdout="LoadState=not-found\nActiveState=inactive\nSubState=dead\nId=foo.service\nDescription=\n")
        with pytest.raises(UnitNotFoundError):
            await backend.get_unit_status("foo.service")


class TestUnitOperations:
    @pytest.mark.asyncio
    async def test_start(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.start_unit("test.service")
        mock.assert_called_once_with("start", "test.service")

    @pytest.mark.asyncio
    async def test_stop(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.stop_unit("test.service")
        mock.assert_called_once_with("stop", "test.service")

    @pytest.mark.asyncio
    async def test_restart(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.restart_unit("test.service")
        mock.assert_called_once_with("restart", "test.service")

    @pytest.mark.asyncio
    async def test_start_failure(self, backend):
        err = SubprocessError(["systemctl", "--user", "start", "test.service"], 5, "access denied")
        backend._run_systemctl = AsyncMock(side_effect=err)
        with pytest.raises(UnitOperationError):
            await backend.start_unit("test.service")


class TestBoolChecks:
    @pytest.mark.asyncio
    async def test_is_active_true(self, backend, mock_systemctl):
        mock_systemctl(stdout="active\n", returncode=0)
        assert await backend.is_active("test.service") is True

    @pytest.mark.asyncio
    async def test_is_active_false(self, backend, mock_systemctl):
        mock_systemctl(stdout="inactive\n", returncode=3)
        assert await backend.is_active("test.service") is False

    @pytest.mark.asyncio
    async def test_is_enabled_true(self, backend, mock_systemctl):
        mock_systemctl(stdout="enabled\n", returncode=0)
        assert await backend.is_enabled("test.service") is True

    @pytest.mark.asyncio
    async def test_is_failed_true(self, backend, mock_systemctl):
        mock_systemctl(stdout="failed\n", returncode=0)
        assert await backend.is_failed("test.service") is True

    @pytest.mark.asyncio
    async def test_is_failed_false(self, backend, mock_systemctl):
        mock_systemctl(stdout="active\n", returncode=1)
        assert await backend.is_failed("test.service") is False

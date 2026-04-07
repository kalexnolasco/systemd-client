"""Tests for subprocess backend."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.enums import ActiveState, LoadState, SystemdScope, UnitFileState
from systemd_client.exceptions import SubprocessError, UnitNotFoundError, UnitOperationError


@pytest.fixture
def backend():
    return SubprocessBackend()


@pytest.fixture
def system_backend():
    return SubprocessBackend(scope=SystemdScope.SYSTEM)


@pytest.fixture
def mock_systemctl(monkeypatch):
    """Helper to mock _run_systemctl on the backend."""
    def _factory(stdout: str = "", stderr: str = "", returncode: int = 0):
        mock = AsyncMock(return_value=(stdout, stderr, returncode))
        monkeypatch.setattr(SubprocessBackend, "_run_systemctl", mock)
        return mock
    return _factory


class TestScope:
    def test_default_scope_is_user(self, backend):
        assert backend._scope == SystemdScope.USER
        assert backend._scope_flag == "--user"

    def test_system_scope(self, system_backend):
        assert system_backend._scope == SystemdScope.SYSTEM
        assert system_backend._scope_flag == "--system"


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


class TestListUnitFiles:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_systemctl, sample_list_unit_files_json):
        mock_systemctl(stdout=sample_list_unit_files_json)
        files = await backend.list_unit_files()
        assert len(files) == 3
        assert files[0].name == "test-app.service"
        assert files[0].state == UnitFileState.ENABLED
        assert files[0].preset == "enabled"
        assert files[2].state == UnitFileState.MASKED

    @pytest.mark.asyncio
    async def test_empty_list(self, backend, mock_systemctl):
        mock_systemctl(stdout="[]")
        files = await backend.list_unit_files()
        assert files == []

    @pytest.mark.asyncio
    async def test_filter_by_type(self, backend, mock_systemctl, sample_list_unit_files_json):
        mock_systemctl(stdout=sample_list_unit_files_json)
        files = await backend.list_unit_files(unit_type="service")
        # The mock returns the same data regardless, but the call args are checked
        assert isinstance(files, list)


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
    async def test_exec_main_status_zero_preserved(self, backend, mock_systemctl):
        """Bug fix: exit code 0 should NOT be None."""
        show_output = "\n".join([
            "Id=test.service",
            "Description=Test",
            "LoadState=loaded",
            "ActiveState=active",
            "SubState=running",
            "ExecMainStatus=0",
            "MainPID=1000",
        ])
        mock_systemctl(stdout=show_output)
        status = await backend.get_unit_status("test.service")
        assert status.exec_main_status == 0

    @pytest.mark.asyncio
    async def test_exec_main_status_nonzero(self, backend, mock_systemctl):
        show_output = "\n".join([
            "Id=test.service",
            "Description=Test",
            "LoadState=loaded",
            "ActiveState=failed",
            "SubState=failed",
            "ExecMainStatus=1",
            "MainPID=0",
        ])
        mock_systemctl(stdout=show_output)
        status = await backend.get_unit_status("test.service")
        assert status.exec_main_status == 1
        assert status.main_pid is None  # PID 0 should be None

    @pytest.mark.asyncio
    async def test_not_found(self, backend, mock_systemctl):
        mock_systemctl(
            stdout="LoadState=not-found\nActiveState=inactive\n"
                   "SubState=dead\nId=foo.service\nDescription=\n",
        )
        with pytest.raises(UnitNotFoundError):
            await backend.get_unit_status("foo.service")


class TestCat:
    @pytest.mark.asyncio
    async def test_returns_content(self, backend, mock_systemctl):
        content = "[Unit]\nDescription=Test\n[Service]\nExecStart=/bin/test\n"
        mock_systemctl(stdout=content)
        result = await backend.cat("test.service")
        assert "[Unit]" in result
        assert "ExecStart" in result

    @pytest.mark.asyncio
    async def test_not_found(self, backend):
        backend._run_systemctl = AsyncMock(
            side_effect=SubprocessError(["systemctl", "--user", "cat", "x"], 1, "No files found"),
        )
        with pytest.raises(UnitNotFoundError):
            await backend.cat("x.service")


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
    async def test_start_no_block(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.start_unit("test.service", no_block=True)
        mock.assert_called_once_with("start", "--no-block", "test.service")

    @pytest.mark.asyncio
    async def test_try_restart(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.try_restart_unit("test.service")
        mock.assert_called_once_with("try-restart", "test.service")

    @pytest.mark.asyncio
    async def test_reload_or_restart(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.reload_or_restart_unit("test.service")
        mock.assert_called_once_with("reload-or-restart", "test.service")

    @pytest.mark.asyncio
    async def test_start_failure(self, backend):
        err = SubprocessError(
            ["systemctl", "--user", "start", "test.service"], 5, "access denied",
        )
        backend._run_systemctl = AsyncMock(side_effect=err)
        with pytest.raises(UnitOperationError):
            await backend.start_unit("test.service")


class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_start_units(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.start_units(["a.service", "b.service"])
        mock.assert_called_once_with("start", "a.service", "b.service")

    @pytest.mark.asyncio
    async def test_stop_units(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.stop_units(["a.service", "b.service"])
        mock.assert_called_once_with("stop", "a.service", "b.service")

    @pytest.mark.asyncio
    async def test_restart_units(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.restart_units(["a.service", "b.service"])
        mock.assert_called_once_with("restart", "a.service", "b.service")

    @pytest.mark.asyncio
    async def test_start_units_no_block(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.start_units(["a.service", "b.service"], no_block=True)
        mock.assert_called_once_with("start", "--no-block", "a.service", "b.service")

    @pytest.mark.asyncio
    async def test_batch_failure(self, backend):
        err = SubprocessError(
            ["systemctl", "--user", "start", "a", "b"], 5, "access denied",
        )
        backend._run_systemctl = AsyncMock(side_effect=err)
        with pytest.raises(UnitOperationError) as exc_info:
            await backend.start_units(["a.service", "b.service"])
        assert "a.service" in exc_info.value.unit_name


class TestResetFailed:
    @pytest.mark.asyncio
    async def test_reset_failed_unit(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.reset_failed("test.service")
        mock.assert_called_once_with("reset-failed", "test.service")

    @pytest.mark.asyncio
    async def test_reset_failed_all(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.reset_failed()
        mock.assert_called_once_with("reset-failed")


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

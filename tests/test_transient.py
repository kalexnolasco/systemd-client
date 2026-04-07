"""Tests for transient units (systemd-run)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import BackendType
from systemd_client.models import TransientResult


@pytest.fixture
def backend():
    return SubprocessBackend()


@pytest.fixture
def mock_systemd_run(monkeypatch):
    """Mock _run_systemd_run on the backend."""
    def _factory(stdout: str = "", stderr: str = ""):
        mock = AsyncMock(return_value=(stdout, stderr, 0))
        monkeypatch.setattr(SubprocessBackend, "_run_systemd_run", mock)
        return mock
    return _factory


class TestSubprocessRunTransient:
    @pytest.mark.asyncio
    async def test_basic_run(self, backend, mock_systemd_run):
        mock = mock_systemd_run(
            stderr="Running as unit: run-test.service\n",
        )
        result = await backend.run_transient(["/bin/echo", "hello"])
        assert result.unit_name == "run-test.service"
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_name(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running as unit: my-task.service\n")
        await backend.run_transient(["/bin/echo"], name="my-task")
        call_args = mock.call_args[0]
        assert "--unit" in call_args
        assert "my-task" in call_args

    @pytest.mark.asyncio
    async def test_run_with_wait(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running as unit: task.service\n")
        await backend.run_transient(["/bin/echo"], wait=True)
        call_args = mock.call_args[0]
        assert "--wait" in call_args

    @pytest.mark.asyncio
    async def test_run_with_properties(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running as unit: task.service\n")
        await backend.run_transient(
            ["/bin/echo"], properties={"MemoryMax": "512M"},
        )
        call_args = mock.call_args[0]
        assert "--property" in call_args
        assert "MemoryMax=512M" in call_args

    @pytest.mark.asyncio
    async def test_run_remain_after_exit(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running as unit: task.service\n")
        await backend.run_transient(["/bin/echo"], remain_after_exit=True)
        call_args = mock.call_args[0]
        assert "--remain-after-exit" in call_args

    @pytest.mark.asyncio
    async def test_run_command_after_separator(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running as unit: task.service\n")
        await backend.run_transient(["/bin/echo", "hello"])
        call_args = mock.call_args[0]
        assert "--" in call_args
        sep_idx = call_args.index("--")
        assert call_args[sep_idx + 1] == "/bin/echo"


class TestSubprocessRunTransientTimer:
    @pytest.mark.asyncio
    async def test_on_calendar(self, backend, mock_systemd_run):
        mock = mock_systemd_run(
            stderr="Running timer as unit: backup.timer\n",
        )
        result = await backend.run_transient_timer(
            ["/bin/backup"], on_calendar="daily",
        )
        assert result.unit_name == "backup.timer"
        call_args = mock.call_args[0]
        assert "--on-calendar" in call_args
        assert "daily" in call_args

    @pytest.mark.asyncio
    async def test_on_active(self, backend, mock_systemd_run):
        mock = mock_systemd_run(
            stderr="Running timer as unit: task.timer\n",
        )
        await backend.run_transient_timer(
            ["/bin/task"], on_active="5min",
        )
        call_args = mock.call_args[0]
        assert "--on-active" in call_args
        assert "5min" in call_args

    @pytest.mark.asyncio
    async def test_with_name(self, backend, mock_systemd_run):
        mock = mock_systemd_run(stderr="Running timer as unit: my-timer.timer\n")
        await backend.run_transient_timer(
            ["/bin/task"], on_calendar="hourly", name="my-timer",
        )
        call_args = mock.call_args[0]
        assert "--unit" in call_args
        assert "my-timer" in call_args


class TestParseTransientResult:
    def test_parse_service(self):
        backend = SubprocessBackend()
        result = backend._parse_transient_result(
            "", "Running as unit: run-u123.service\n",
        )
        assert result.unit_name == "run-u123.service"

    def test_parse_timer(self):
        backend = SubprocessBackend()
        result = backend._parse_transient_result(
            "", "Running timer as unit: backup.timer\n",
        )
        assert result.unit_name == "backup.timer"

    def test_parse_empty(self):
        backend = SubprocessBackend()
        result = backend._parse_transient_result("", "")
        assert result.unit_name == ""
        assert result.pid is None


class TestTransientResultModel:
    def test_creation(self):
        r = TransientResult(unit_name="test.service", pid=1234)
        assert r.unit_name == "test.service"
        assert r.pid == 1234

    def test_defaults(self):
        r = TransientResult(unit_name="test.service")
        assert r.pid is None

    def test_frozen(self):
        r = TransientResult(unit_name="test.service")
        with pytest.raises(AttributeError):
            r.unit_name = "other"  # type: ignore[misc]


class TestClientRunMethods:
    @pytest.fixture
    def mock_backend(self):
        backend = AsyncMock()
        backend.run_transient = AsyncMock(
            return_value=TransientResult("task.service", 123),
        )
        backend.run_transient_timer = AsyncMock(
            return_value=TransientResult("task.timer"),
        )
        backend.close = AsyncMock()
        return backend

    @pytest.mark.asyncio
    async def test_async_run(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        result = await client.run("/bin/echo hello")
        assert result.unit_name == "task.service"

    @pytest.mark.asyncio
    async def test_async_run_on_calendar(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        result = await client.run_on_calendar("daily", "/bin/backup")
        assert result.unit_name == "task.timer"

    def test_sync_run(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            result = client.run("/bin/echo")
            assert result.unit_name == "task.service"

    def test_sync_run_on_calendar(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            result = client.run_on_calendar("daily", "/bin/backup")
            assert result.unit_name == "task.timer"

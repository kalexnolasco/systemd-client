"""Tests for resource control and monitoring."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import BackendType
from systemd_client.models import ResourceUsage, SocketInfo, TimerInfo


@pytest.fixture
def backend():
    return SubprocessBackend()


@pytest.fixture
def mock_systemctl(monkeypatch):
    def _factory(stdout: str = "", stderr: str = "", returncode: int = 0):
        mock = AsyncMock(return_value=(stdout, stderr, returncode))
        monkeypatch.setattr(SubprocessBackend, "_run_systemctl", mock)
        return mock
    return _factory


class TestSetProperty:
    @pytest.mark.asyncio
    async def test_calls_set_property(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.set_property("test.service", {"MemoryMax": "512M"})
        call_args = mock.call_args[0]
        assert "set-property" in call_args
        assert "test.service" in call_args
        assert "MemoryMax=512M" in call_args


class TestGetResourceUsage:
    @pytest.mark.asyncio
    async def test_parses_usage(self, backend, mock_systemctl):
        mock_systemctl(stdout="\n".join([
            "CPUUsageNSec=1500000000",
            "MemoryCurrent=52428800",
            "MemoryPeak=104857600",
            "TasksCurrent=5",
            "IOReadBytes=1048576",
            "IOWriteBytes=2097152",
        ]))
        usage = await backend.get_resource_usage("test.service")
        assert usage.cpu_usage_nsec == 1500000000
        assert usage.memory_current == 52428800
        assert usage.memory_peak == 104857600
        assert usage.tasks_current == 5
        assert usage.io_read_bytes == 1048576
        assert usage.io_write_bytes == 2097152

    @pytest.mark.asyncio
    async def test_not_set_returns_none(self, backend, mock_systemctl):
        mock_systemctl(stdout="CPUUsageNSec=[not set]\nMemoryCurrent=[not set]\n")
        usage = await backend.get_resource_usage("test.service")
        assert usage.cpu_usage_nsec is None
        assert usage.memory_current is None


class TestListTimers:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_systemctl):
        data = [
            {"unit": "backup.timer", "left": "5h left", "activates": "backup.service"},
        ]
        mock_systemctl(stdout=json.dumps(data))
        timers = await backend.list_timers()
        assert len(timers) == 1
        assert timers[0].name == "backup.timer"
        assert timers[0].activates == "backup.service"

    @pytest.mark.asyncio
    async def test_empty(self, backend, mock_systemctl):
        mock_systemctl(stdout="[]")
        assert await backend.list_timers() == []


class TestListSockets:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_systemctl):
        data = [
            {"unit": "app.socket", "listen": "/run/app.sock", "type": "Stream"},
        ]
        mock_systemctl(stdout=json.dumps(data))
        sockets = await backend.list_sockets()
        assert len(sockets) == 1
        assert sockets[0].listen == "/run/app.sock"


class TestListDependencies:
    @pytest.mark.asyncio
    async def test_parses_output(self, backend, mock_systemctl):
        mock_systemctl(stdout="test.service\nnetwork.target\nsyslog.target\n")
        deps = await backend.list_dependencies("test.service")
        assert "network.target" in deps
        assert "syslog.target" in deps


class TestKillUnit:
    @pytest.mark.asyncio
    async def test_sends_signal(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.kill_unit("test.service", "SIGHUP")
        call_args = mock.call_args[0]
        assert "kill" in call_args
        assert "--signal=SIGHUP" in call_args


class TestResourceModels:
    def test_resource_usage(self):
        r = ResourceUsage(cpu_usage_nsec=1000, memory_current=2000)
        assert r.cpu_usage_nsec == 1000
        assert r.tasks_current is None

    def test_timer_info(self):
        t = TimerInfo(name="backup.timer", time_left="5h left")
        assert t.name == "backup.timer"

    def test_socket_info(self):
        s = SocketInfo(name="app.socket", listen="/run/app.sock", type="Stream")
        assert s.listen == "/run/app.sock"


class TestClientResourceMethods:
    @pytest.fixture
    def mock_backend(self):
        backend = AsyncMock()
        backend.set_property = AsyncMock()
        backend.get_resource_usage = AsyncMock(
            return_value=ResourceUsage(memory_current=1024),
        )
        backend.list_timers = AsyncMock(return_value=[])
        backend.list_sockets = AsyncMock(return_value=[])
        backend.list_dependencies = AsyncMock(return_value=["a.target"])
        backend.kill_unit = AsyncMock()
        backend.close = AsyncMock()
        return backend

    @pytest.mark.asyncio
    async def test_async_set_property(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        await client.set_property("test.service", {"MemoryMax": "512M"})
        mock_backend.set_property.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_get_resource_usage(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        usage = await client.get_resource_usage("test.service")
        assert usage.memory_current == 1024

    @pytest.mark.asyncio
    async def test_async_list_timers(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        assert await client.list_timers() == []

    @pytest.mark.asyncio
    async def test_async_kill(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        await client.kill("test.service", "SIGKILL")
        mock_backend.kill_unit.assert_called_once_with("test.service", "SIGKILL")

    def test_sync_list_dependencies(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            deps = client.list_dependencies("test.service")
            assert deps == ["a.target"]

"""Tests for the high-level client layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import (
    ActiveState,
    BackendType,
    LoadState,
    SubState,
    SystemdScope,
    UnitFileState,
)
from systemd_client.models import EnableResult, UnitFileInfo, UnitInfo, UnitStatus


@pytest.fixture
def mock_backend():
    """Create a mock backend with all methods as AsyncMock."""
    backend = AsyncMock()
    backend.list_units = AsyncMock(return_value=[
        UnitInfo("test.service", "Test", LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING),
    ])
    backend.list_unit_files = AsyncMock(return_value=[
        UnitFileInfo("test.service", UnitFileState.ENABLED, preset="enabled"),
    ])
    backend.get_unit_status = AsyncMock(return_value=UnitStatus(
        name="test.service",
        description="Test",
        load_state=LoadState.LOADED,
        active_state=ActiveState.ACTIVE,
        sub_state=SubState.RUNNING,
    ))
    backend.cat = AsyncMock(return_value="[Unit]\nDescription=Test\n")
    backend.start_unit = AsyncMock()
    backend.stop_unit = AsyncMock()
    backend.restart_unit = AsyncMock()
    backend.reload_unit = AsyncMock()
    backend.try_restart_unit = AsyncMock()
    backend.reload_or_restart_unit = AsyncMock()
    backend.start_units = AsyncMock()
    backend.stop_units = AsyncMock()
    backend.restart_units = AsyncMock()
    backend.enable_unit = AsyncMock(return_value=EnableResult())
    backend.disable_unit = AsyncMock(return_value=EnableResult())
    backend.mask_unit = AsyncMock(return_value=EnableResult())
    backend.unmask_unit = AsyncMock(return_value=EnableResult())
    backend.is_active = AsyncMock(return_value=True)
    backend.is_enabled = AsyncMock(return_value=True)
    backend.is_failed = AsyncMock(return_value=False)
    backend.daemon_reload = AsyncMock()
    backend.reset_failed = AsyncMock()
    backend.close = AsyncMock()
    return backend


@pytest.fixture
def async_client(mock_backend):
    client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
    client._backend = mock_backend
    return client


class TestAsyncSystemdClient:
    @pytest.mark.asyncio
    async def test_list_units(self, async_client, mock_backend):
        units = await async_client.list_units()
        assert len(units) == 1
        mock_backend.list_units.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_unit_files(self, async_client, mock_backend):
        files = await async_client.list_unit_files()
        assert len(files) == 1
        assert files[0].name == "test.service"

    @pytest.mark.asyncio
    async def test_status(self, async_client, mock_backend):
        status = await async_client.status("test.service")
        assert status.name == "test.service"

    @pytest.mark.asyncio
    async def test_cat(self, async_client, mock_backend):
        content = await async_client.cat("test.service")
        assert "[Unit]" in content

    @pytest.mark.asyncio
    async def test_start(self, async_client, mock_backend):
        await async_client.start("test.service")
        mock_backend.start_unit.assert_called_once_with("test.service", no_block=False)

    @pytest.mark.asyncio
    async def test_start_no_block(self, async_client, mock_backend):
        await async_client.start("test.service", no_block=True)
        mock_backend.start_unit.assert_called_once_with("test.service", no_block=True)

    @pytest.mark.asyncio
    async def test_stop(self, async_client, mock_backend):
        await async_client.stop("test.service")
        mock_backend.stop_unit.assert_called_once_with("test.service", no_block=False)

    @pytest.mark.asyncio
    async def test_restart(self, async_client, mock_backend):
        await async_client.restart("test.service")
        mock_backend.restart_unit.assert_called_once_with("test.service", no_block=False)

    @pytest.mark.asyncio
    async def test_try_restart(self, async_client, mock_backend):
        await async_client.try_restart("test.service")
        mock_backend.try_restart_unit.assert_called_once_with("test.service", no_block=False)

    @pytest.mark.asyncio
    async def test_reload_or_restart(self, async_client, mock_backend):
        await async_client.reload_or_restart("test.service")
        mock_backend.reload_or_restart_unit.assert_called_once_with(
            "test.service", no_block=False,
        )

    @pytest.mark.asyncio
    async def test_start_units(self, async_client, mock_backend):
        await async_client.start_units(["a.service", "b.service"])
        mock_backend.start_units.assert_called_once_with(
            ["a.service", "b.service"], no_block=False,
        )

    @pytest.mark.asyncio
    async def test_stop_units(self, async_client, mock_backend):
        await async_client.stop_units(["a.service", "b.service"])
        mock_backend.stop_units.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_units(self, async_client, mock_backend):
        await async_client.restart_units(["a.service", "b.service"])
        mock_backend.restart_units.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable(self, async_client, mock_backend):
        result = await async_client.enable("test.service")
        assert isinstance(result, EnableResult)

    @pytest.mark.asyncio
    async def test_is_active(self, async_client, mock_backend):
        assert await async_client.is_active("test.service") is True

    @pytest.mark.asyncio
    async def test_daemon_reload(self, async_client, mock_backend):
        await async_client.daemon_reload()
        mock_backend.daemon_reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_failed(self, async_client, mock_backend):
        await async_client.reset_failed("test.service")
        mock_backend.reset_failed.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_reset_failed_all(self, async_client, mock_backend):
        await async_client.reset_failed()
        mock_backend.reset_failed.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        async with client as c:
            assert c is client
        mock_backend.close.assert_called_once()

    def test_repr(self):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS, scope=SystemdScope.USER)
        r = repr(client)
        assert "AsyncSystemdClient" in r
        assert "subprocess" in r
        assert "user" in r

    def test_repr_system_scope(self):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS, scope=SystemdScope.SYSTEM)
        r = repr(client)
        assert "system" in r


class TestSyncSystemdClient:
    def test_list_units(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            units = client.list_units()
            assert len(units) == 1

    def test_list_unit_files(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            files = client.list_unit_files()
            assert len(files) == 1

    def test_is_active(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            assert client.is_active("test.service") is True

    def test_cat(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            content = client.cat("test.service")
            assert "[Unit]" in content

    def test_context_manager(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            with SystemdClient(backend=BackendType.SUBPROCESS) as client:
                client._async_client._backend = mock_backend
                assert client is not None
            mock_backend.close.assert_called()

    def test_repr(self):
        client = SystemdClient(backend=BackendType.SUBPROCESS)
        r = repr(client)
        assert "SystemdClient" in r
        assert "subprocess" in r

    def test_reset_failed(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            client.reset_failed("test.service")
            mock_backend.reset_failed.assert_called_once_with("test.service")

    def test_try_restart(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            client.try_restart("test.service")
            mock_backend.try_restart_unit.assert_called_once()

    def test_reload_or_restart(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            client.reload_or_restart("test.service")
            mock_backend.reload_or_restart_unit.assert_called_once()

    def test_start_units(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            client.start_units(["a.service", "b.service"])
            mock_backend.start_units.assert_called_once()

"""Tests for the high-level client layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import ActiveState, BackendType, LoadState, SubState
from systemd_client.models import EnableResult, UnitInfo, UnitStatus


@pytest.fixture
def mock_backend():
    """Create a mock backend with all methods as AsyncMock."""
    backend = AsyncMock()
    backend.list_units = AsyncMock(return_value=[
        UnitInfo("test.service", "Test", LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING),
    ])
    backend.get_unit_status = AsyncMock(return_value=UnitStatus(
        name="test.service",
        description="Test",
        load_state=LoadState.LOADED,
        active_state=ActiveState.ACTIVE,
        sub_state=SubState.RUNNING,
    ))
    backend.start_unit = AsyncMock()
    backend.stop_unit = AsyncMock()
    backend.restart_unit = AsyncMock()
    backend.reload_unit = AsyncMock()
    backend.enable_unit = AsyncMock(return_value=EnableResult())
    backend.disable_unit = AsyncMock(return_value=EnableResult())
    backend.mask_unit = AsyncMock(return_value=EnableResult())
    backend.unmask_unit = AsyncMock(return_value=EnableResult())
    backend.is_active = AsyncMock(return_value=True)
    backend.is_enabled = AsyncMock(return_value=True)
    backend.is_failed = AsyncMock(return_value=False)
    backend.daemon_reload = AsyncMock()
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
    async def test_status(self, async_client, mock_backend):
        status = await async_client.status("test.service")
        assert status.name == "test.service"

    @pytest.mark.asyncio
    async def test_start(self, async_client, mock_backend):
        await async_client.start("test.service")
        mock_backend.start_unit.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_stop(self, async_client, mock_backend):
        await async_client.stop("test.service")
        mock_backend.stop_unit.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_restart(self, async_client, mock_backend):
        await async_client.restart("test.service")
        mock_backend.restart_unit.assert_called_once_with("test.service")

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


class TestSyncSystemdClient:
    def test_list_units(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            units = client.list_units()
            assert len(units) == 1

    def test_is_active(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            assert client.is_active("test.service") is True

"""High-level async and sync systemd clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from systemd_client._sync import run_sync
from systemd_client.backends import AbstractBackend, get_backend
from systemd_client.enums import BackendType, JournalPriority
from systemd_client.journal._query import JournalQuery
from systemd_client.journal._reader import AsyncJournalReader, JournalReader

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from systemd_client.models import EnableResult, JournalEntry, UnitInfo, UnitStatus


class AsyncSystemdClient:
    """Async-first systemd client for user services."""

    def __init__(self, backend: BackendType = BackendType.AUTO) -> None:
        self._backend: AbstractBackend = get_backend(backend)
        self._journal = AsyncJournalReader()

    async def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        """List systemd user units."""
        return await self._backend.list_units(unit_type=unit_type, state=state)

    async def status(self, unit_name: str) -> UnitStatus:
        """Get detailed status of a unit."""
        return await self._backend.get_unit_status(unit_name)

    async def start(self, unit_name: str) -> None:
        """Start a unit."""
        await self._backend.start_unit(unit_name)

    async def stop(self, unit_name: str) -> None:
        """Stop a unit."""
        await self._backend.stop_unit(unit_name)

    async def restart(self, unit_name: str) -> None:
        """Restart a unit."""
        await self._backend.restart_unit(unit_name)

    async def reload(self, unit_name: str) -> None:
        """Reload a unit."""
        await self._backend.reload_unit(unit_name)

    async def enable(self, unit_name: str) -> EnableResult:
        """Enable a unit."""
        return await self._backend.enable_unit(unit_name)

    async def disable(self, unit_name: str) -> EnableResult:
        """Disable a unit."""
        return await self._backend.disable_unit(unit_name)

    async def mask(self, unit_name: str) -> EnableResult:
        """Mask a unit."""
        return await self._backend.mask_unit(unit_name)

    async def unmask(self, unit_name: str) -> EnableResult:
        """Unmask a unit."""
        return await self._backend.unmask_unit(unit_name)

    async def is_active(self, unit_name: str) -> bool:
        """Check if a unit is active."""
        return await self._backend.is_active(unit_name)

    async def is_enabled(self, unit_name: str) -> bool:
        """Check if a unit is enabled."""
        return await self._backend.is_enabled(unit_name)

    async def is_failed(self, unit_name: str) -> bool:
        """Check if a unit is in failed state."""
        return await self._backend.is_failed(unit_name)

    async def daemon_reload(self) -> None:
        """Reload the systemd daemon configuration."""
        await self._backend.daemon_reload()

    async def journal(
        self,
        unit: str | None = None,
        lines: int | None = None,
        since: str | None = None,
        until: str | None = None,
        priority: JournalPriority | None = None,
        grep: str | None = None,
    ) -> list[JournalEntry]:
        """Query journal entries."""
        q = JournalQuery(
            unit=unit, lines=lines, since=since, until=until,
            priority=priority, grep=grep,
        )
        return await self._journal.query(q)

    async def journal_follow(
        self,
        unit: str | None = None,
        lines: int | None = None,
        priority: JournalPriority | None = None,
    ) -> AsyncIterator[JournalEntry]:
        """Follow journal output as an async generator."""
        q = JournalQuery(unit=unit, lines=lines, priority=priority)
        async for entry in self._journal.follow(q):
            yield entry


class SystemdClient:
    """Synchronous systemd client wrapping AsyncSystemdClient."""

    def __init__(self, backend: BackendType = BackendType.AUTO) -> None:
        self._async_client = AsyncSystemdClient(backend=backend)
        self._journal = JournalReader()

    def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        """List systemd user units."""
        return run_sync(self._async_client.list_units(unit_type=unit_type, state=state))  # type: ignore[return-value]

    def status(self, unit_name: str) -> UnitStatus:
        """Get detailed status of a unit."""
        return run_sync(self._async_client.status(unit_name))  # type: ignore[return-value]

    def start(self, unit_name: str) -> None:
        """Start a unit."""
        run_sync(self._async_client.start(unit_name))

    def stop(self, unit_name: str) -> None:
        """Stop a unit."""
        run_sync(self._async_client.stop(unit_name))

    def restart(self, unit_name: str) -> None:
        """Restart a unit."""
        run_sync(self._async_client.restart(unit_name))

    def reload(self, unit_name: str) -> None:
        """Reload a unit."""
        run_sync(self._async_client.reload(unit_name))

    def enable(self, unit_name: str) -> EnableResult:
        """Enable a unit."""
        return run_sync(self._async_client.enable(unit_name))  # type: ignore[return-value]

    def disable(self, unit_name: str) -> EnableResult:
        """Disable a unit."""
        return run_sync(self._async_client.disable(unit_name))  # type: ignore[return-value]

    def mask(self, unit_name: str) -> EnableResult:
        """Mask a unit."""
        return run_sync(self._async_client.mask(unit_name))  # type: ignore[return-value]

    def unmask(self, unit_name: str) -> EnableResult:
        """Unmask a unit."""
        return run_sync(self._async_client.unmask(unit_name))  # type: ignore[return-value]

    def is_active(self, unit_name: str) -> bool:
        """Check if a unit is active."""
        return run_sync(self._async_client.is_active(unit_name))  # type: ignore[return-value]

    def is_enabled(self, unit_name: str) -> bool:
        """Check if a unit is enabled."""
        return run_sync(self._async_client.is_enabled(unit_name))  # type: ignore[return-value]

    def is_failed(self, unit_name: str) -> bool:
        """Check if a unit is in failed state."""
        return run_sync(self._async_client.is_failed(unit_name))  # type: ignore[return-value]

    def daemon_reload(self) -> None:
        """Reload the systemd daemon configuration."""
        run_sync(self._async_client.daemon_reload())

    def journal(
        self,
        unit: str | None = None,
        lines: int | None = None,
        since: str | None = None,
        until: str | None = None,
        priority: JournalPriority | None = None,
        grep: str | None = None,
    ) -> list[JournalEntry]:
        """Query journal entries."""
        q = JournalQuery(
            unit=unit, lines=lines, since=since, until=until,
            priority=priority, grep=grep,
        )
        return self._journal.query(q)

    def journal_follow(
        self,
        unit: str | None = None,
        lines: int | None = None,
        priority: JournalPriority | None = None,
    ) -> Iterator[JournalEntry]:
        """Follow journal output as a synchronous iterator."""
        q = JournalQuery(unit=unit, lines=lines, priority=priority)
        return self._journal.follow(q)

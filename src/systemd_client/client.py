"""High-level async and sync systemd clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from systemd_client._sync import run_sync
from systemd_client.backends import AbstractBackend, get_backend
from systemd_client.enums import BackendType, JournalPriority, SystemdScope
from systemd_client.journal._query import JournalQuery
from systemd_client.journal._reader import AsyncJournalReader, JournalReader

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from types import TracebackType

    from systemd_client.models import (
        EnableResult,
        JournalEntry,
        ResourceUsage,
        SocketInfo,
        TimerInfo,
        TransientResult,
        UnitFile,
        UnitFileInfo,
        UnitInfo,
        UnitStatus,
    )


class AsyncSystemdClient:
    """Async-first systemd client for user or system services."""

    def __init__(
        self,
        backend: BackendType = BackendType.AUTO,
        scope: SystemdScope = SystemdScope.USER,
    ) -> None:
        self._scope = scope
        self._backend_type = backend
        self._backend: AbstractBackend = get_backend(backend, scope=scope)
        self._journal = AsyncJournalReader(scope=scope)

    async def __aenter__(self) -> AsyncSystemdClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Release backend resources."""
        await self._backend.close()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"backend={self._backend_type!r}, scope={self._scope!r})"
        )

    async def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        """List systemd units."""
        return await self._backend.list_units(unit_type=unit_type, state=state)

    async def list_unit_files(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitFileInfo]:
        """List installed unit files."""
        return await self._backend.list_unit_files(unit_type=unit_type, state=state)

    async def status(self, unit_name: str) -> UnitStatus:
        """Get detailed status of a unit."""
        return await self._backend.get_unit_status(unit_name)

    async def cat(self, unit_name: str) -> str:
        """Show the content of a unit file."""
        return await self._backend.cat(unit_name)

    async def start(self, unit_name: str, no_block: bool = False) -> None:
        """Start a unit."""
        await self._backend.start_unit(unit_name, no_block=no_block)

    async def stop(self, unit_name: str, no_block: bool = False) -> None:
        """Stop a unit."""
        await self._backend.stop_unit(unit_name, no_block=no_block)

    async def restart(self, unit_name: str, no_block: bool = False) -> None:
        """Restart a unit."""
        await self._backend.restart_unit(unit_name, no_block=no_block)

    async def reload(self, unit_name: str, no_block: bool = False) -> None:
        """Reload a unit."""
        await self._backend.reload_unit(unit_name, no_block=no_block)

    async def try_restart(self, unit_name: str, no_block: bool = False) -> None:
        """Restart a unit if it is active, otherwise do nothing."""
        await self._backend.try_restart_unit(unit_name, no_block=no_block)

    async def reload_or_restart(self, unit_name: str, no_block: bool = False) -> None:
        """Reload a unit if it supports it, otherwise restart."""
        await self._backend.reload_or_restart_unit(unit_name, no_block=no_block)

    async def start_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Start multiple units in a single operation."""
        await self._backend.start_units(unit_names, no_block=no_block)

    async def stop_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Stop multiple units in a single operation."""
        await self._backend.stop_units(unit_names, no_block=no_block)

    async def restart_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Restart multiple units in a single operation."""
        await self._backend.restart_units(unit_names, no_block=no_block)

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

    async def reset_failed(self, unit_name: str | None = None) -> None:
        """Reset the failed state of a unit, or all units if no name given."""
        await self._backend.reset_failed(unit_name)

    async def set_property(self, unit_name: str, properties: dict[str, str]) -> None:
        """Set runtime properties on a unit (cgroup limits, etc.)."""
        await self._backend.set_property(unit_name, properties)

    async def get_resource_usage(self, unit_name: str) -> ResourceUsage:
        """Get resource usage statistics for a unit."""
        return await self._backend.get_resource_usage(unit_name)

    async def list_timers(self) -> list[TimerInfo]:
        """List active timers."""
        return await self._backend.list_timers()

    async def list_sockets(self) -> list[SocketInfo]:
        """List active sockets."""
        return await self._backend.list_sockets()

    async def list_dependencies(self, unit_name: str) -> list[str]:
        """List dependency tree of a unit."""
        return await self._backend.list_dependencies(unit_name)

    async def kill(self, unit_name: str, signal: str = "SIGTERM") -> None:
        """Send a signal to a unit's processes."""
        await self._backend.kill_unit(unit_name, signal)

    async def run(
        self,
        command: str | list[str],
        *,
        name: str | None = None,
        wait: bool = False,
        properties: dict[str, str] | None = None,
        remain_after_exit: bool = False,
    ) -> TransientResult:
        """Run a command as a transient systemd service (systemd-run)."""
        cmd = [command] if isinstance(command, str) else command
        return await self._backend.run_transient(
            cmd, name=name, wait=wait, properties=properties,
            remain_after_exit=remain_after_exit,
        )

    async def run_on_calendar(
        self,
        on_calendar: str,
        command: str | list[str],
        *,
        name: str | None = None,
    ) -> TransientResult:
        """Schedule a command as a transient timer (systemd-run --on-calendar)."""
        cmd = [command] if isinstance(command, str) else command
        return await self._backend.run_transient_timer(
            cmd, on_calendar=on_calendar, name=name,
        )

    async def install(self, unit_file: UnitFile) -> str:
        """Install a unit file. Returns the path where it was written."""
        return await self._backend.install_unit_file(unit_file)

    async def uninstall(self, unit_name: str) -> None:
        """Remove an installed unit file and daemon-reload."""
        await self._backend.uninstall_unit_file(unit_name)

    async def edit(self, unit_name: str, overrides: dict[str, dict[str, str]]) -> str:
        """Create a drop-in override for a unit. Returns the override path."""
        return await self._backend.edit_unit_file(unit_name, overrides)

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

    def __init__(
        self,
        backend: BackendType = BackendType.AUTO,
        scope: SystemdScope = SystemdScope.USER,
    ) -> None:
        self._async_client = AsyncSystemdClient(backend=backend, scope=scope)
        self._journal = JournalReader(scope=scope)

    def __enter__(self) -> SystemdClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release backend resources."""
        run_sync(self._async_client.close())

    def __repr__(self) -> str:
        return repr(self._async_client).replace("AsyncSystemdClient", "SystemdClient")

    def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        """List systemd units."""
        return run_sync(self._async_client.list_units(unit_type=unit_type, state=state))

    def list_unit_files(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitFileInfo]:
        """List installed unit files."""
        return run_sync(self._async_client.list_unit_files(unit_type=unit_type, state=state))

    def status(self, unit_name: str) -> UnitStatus:
        """Get detailed status of a unit."""
        return run_sync(self._async_client.status(unit_name))

    def cat(self, unit_name: str) -> str:
        """Show the content of a unit file."""
        return run_sync(self._async_client.cat(unit_name))

    def start(self, unit_name: str, no_block: bool = False) -> None:
        """Start a unit."""
        run_sync(self._async_client.start(unit_name, no_block=no_block))

    def stop(self, unit_name: str, no_block: bool = False) -> None:
        """Stop a unit."""
        run_sync(self._async_client.stop(unit_name, no_block=no_block))

    def restart(self, unit_name: str, no_block: bool = False) -> None:
        """Restart a unit."""
        run_sync(self._async_client.restart(unit_name, no_block=no_block))

    def reload(self, unit_name: str, no_block: bool = False) -> None:
        """Reload a unit."""
        run_sync(self._async_client.reload(unit_name, no_block=no_block))

    def try_restart(self, unit_name: str, no_block: bool = False) -> None:
        """Restart a unit if it is active, otherwise do nothing."""
        run_sync(self._async_client.try_restart(unit_name, no_block=no_block))

    def reload_or_restart(self, unit_name: str, no_block: bool = False) -> None:
        """Reload a unit if it supports it, otherwise restart."""
        run_sync(self._async_client.reload_or_restart(unit_name, no_block=no_block))

    def start_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Start multiple units in a single operation."""
        run_sync(self._async_client.start_units(unit_names, no_block=no_block))

    def stop_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Stop multiple units in a single operation."""
        run_sync(self._async_client.stop_units(unit_names, no_block=no_block))

    def restart_units(self, unit_names: list[str], no_block: bool = False) -> None:
        """Restart multiple units in a single operation."""
        run_sync(self._async_client.restart_units(unit_names, no_block=no_block))

    def enable(self, unit_name: str) -> EnableResult:
        """Enable a unit."""
        return run_sync(self._async_client.enable(unit_name))

    def disable(self, unit_name: str) -> EnableResult:
        """Disable a unit."""
        return run_sync(self._async_client.disable(unit_name))

    def mask(self, unit_name: str) -> EnableResult:
        """Mask a unit."""
        return run_sync(self._async_client.mask(unit_name))

    def unmask(self, unit_name: str) -> EnableResult:
        """Unmask a unit."""
        return run_sync(self._async_client.unmask(unit_name))

    def is_active(self, unit_name: str) -> bool:
        """Check if a unit is active."""
        return run_sync(self._async_client.is_active(unit_name))

    def is_enabled(self, unit_name: str) -> bool:
        """Check if a unit is enabled."""
        return run_sync(self._async_client.is_enabled(unit_name))

    def is_failed(self, unit_name: str) -> bool:
        """Check if a unit is in failed state."""
        return run_sync(self._async_client.is_failed(unit_name))

    def daemon_reload(self) -> None:
        """Reload the systemd daemon configuration."""
        run_sync(self._async_client.daemon_reload())

    def reset_failed(self, unit_name: str | None = None) -> None:
        """Reset the failed state of a unit, or all units if no name given."""
        run_sync(self._async_client.reset_failed(unit_name))

    def set_property(self, unit_name: str, properties: dict[str, str]) -> None:
        """Set runtime properties on a unit (cgroup limits, etc.)."""
        run_sync(self._async_client.set_property(unit_name, properties))

    def get_resource_usage(self, unit_name: str) -> ResourceUsage:
        """Get resource usage statistics for a unit."""
        return run_sync(self._async_client.get_resource_usage(unit_name))

    def list_timers(self) -> list[TimerInfo]:
        """List active timers."""
        return run_sync(self._async_client.list_timers())

    def list_sockets(self) -> list[SocketInfo]:
        """List active sockets."""
        return run_sync(self._async_client.list_sockets())

    def list_dependencies(self, unit_name: str) -> list[str]:
        """List dependency tree of a unit."""
        return run_sync(self._async_client.list_dependencies(unit_name))

    def kill(self, unit_name: str, signal: str = "SIGTERM") -> None:
        """Send a signal to a unit's processes."""
        run_sync(self._async_client.kill(unit_name, signal))

    def run(
        self,
        command: str | list[str],
        *,
        name: str | None = None,
        wait: bool = False,
        properties: dict[str, str] | None = None,
        remain_after_exit: bool = False,
    ) -> TransientResult:
        """Run a command as a transient systemd service (systemd-run)."""
        return run_sync(self._async_client.run(
            command, name=name, wait=wait, properties=properties,
            remain_after_exit=remain_after_exit,
        ))

    def run_on_calendar(
        self,
        on_calendar: str,
        command: str | list[str],
        *,
        name: str | None = None,
    ) -> TransientResult:
        """Schedule a command as a transient timer (systemd-run --on-calendar)."""
        return run_sync(self._async_client.run_on_calendar(
            on_calendar, command, name=name,
        ))

    def install(self, unit_file: UnitFile) -> str:
        """Install a unit file. Returns the path where it was written."""
        return run_sync(self._async_client.install(unit_file))

    def uninstall(self, unit_name: str) -> None:
        """Remove an installed unit file and daemon-reload."""
        run_sync(self._async_client.uninstall(unit_name))

    def edit(self, unit_name: str, overrides: dict[str, dict[str, str]]) -> str:
        """Create a drop-in override for a unit. Returns the override path."""
        return run_sync(self._async_client.edit(unit_name, overrides))

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

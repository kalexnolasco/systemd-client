"""Abstract backend interface for systemd operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systemd_client.models import (
        EnableResult,
        ResourceUsage,
        SocketInfo,
        TimerInfo,
        TransientResult,
        UnitFile,
        UnitFileInfo,
        UnitInfo,
        UnitStatus,
    )


class AbstractBackend(ABC):
    """Abstract base class for systemd backends.

    All methods are async. Sync clients wrap these via run_sync().
    """

    @abstractmethod
    async def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        ...

    @abstractmethod
    async def list_unit_files(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitFileInfo]:
        ...

    @abstractmethod
    async def get_unit_status(self, unit_name: str) -> UnitStatus:
        ...

    @abstractmethod
    async def cat(self, unit_name: str) -> str:
        ...

    @abstractmethod
    async def start_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def stop_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def reload_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def try_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def reload_or_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def start_units(self, unit_names: list[str], no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def stop_units(self, unit_names: list[str], no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def restart_units(self, unit_names: list[str], no_block: bool = False) -> None:
        ...

    @abstractmethod
    async def enable_unit(self, unit_name: str) -> EnableResult:
        ...

    @abstractmethod
    async def disable_unit(self, unit_name: str) -> EnableResult:
        ...

    @abstractmethod
    async def mask_unit(self, unit_name: str) -> EnableResult:
        ...

    @abstractmethod
    async def unmask_unit(self, unit_name: str) -> EnableResult:
        ...

    @abstractmethod
    async def daemon_reload(self) -> None:
        ...

    @abstractmethod
    async def reset_failed(self, unit_name: str | None = None) -> None:
        ...

    @abstractmethod
    async def get_unit_file_state(self, unit_name: str) -> str:
        ...

    @abstractmethod
    async def is_active(self, unit_name: str) -> bool:
        ...

    @abstractmethod
    async def is_enabled(self, unit_name: str) -> bool:
        ...

    @abstractmethod
    async def is_failed(self, unit_name: str) -> bool:
        ...

    @abstractmethod
    async def set_property(self, unit_name: str, properties: dict[str, str]) -> None:
        ...

    @abstractmethod
    async def get_resource_usage(self, unit_name: str) -> ResourceUsage:
        ...

    @abstractmethod
    async def list_timers(self) -> list[TimerInfo]:
        ...

    @abstractmethod
    async def list_sockets(self) -> list[SocketInfo]:
        ...

    @abstractmethod
    async def list_dependencies(self, unit_name: str) -> list[str]:
        ...

    @abstractmethod
    async def kill_unit(self, unit_name: str, signal: str = "SIGTERM") -> None:
        ...

    @abstractmethod
    async def run_transient(
        self,
        command: list[str],
        *,
        name: str | None = None,
        properties: dict[str, str] | None = None,
        remain_after_exit: bool = False,
        wait: bool = False,
    ) -> TransientResult:
        ...

    @abstractmethod
    async def run_transient_timer(
        self,
        command: list[str],
        *,
        on_calendar: str | None = None,
        on_active: str | None = None,
        name: str | None = None,
    ) -> TransientResult:
        ...

    @abstractmethod
    async def install_unit_file(self, unit_file: UnitFile) -> str:
        """Write a unit file to the appropriate directory. Returns the written path."""
        ...

    @abstractmethod
    async def uninstall_unit_file(self, unit_name: str) -> None:
        """Remove a unit file and daemon-reload."""
        ...

    @abstractmethod
    async def edit_unit_file(
        self,
        unit_name: str,
        overrides: dict[str, dict[str, str]],
    ) -> str:
        """Create a drop-in override file. Returns the written path."""
        ...

    async def close(self) -> None:  # noqa: B027
        """Release backend resources. Override in subclasses that hold connections."""

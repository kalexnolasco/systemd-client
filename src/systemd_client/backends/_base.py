"""Abstract backend interface for systemd operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systemd_client.models import EnableResult, UnitInfo, UnitStatus


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
    async def get_unit_status(self, unit_name: str) -> UnitStatus:
        ...

    @abstractmethod
    async def start_unit(self, unit_name: str) -> None:
        ...

    @abstractmethod
    async def stop_unit(self, unit_name: str) -> None:
        ...

    @abstractmethod
    async def restart_unit(self, unit_name: str) -> None:
        ...

    @abstractmethod
    async def reload_unit(self, unit_name: str) -> None:
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

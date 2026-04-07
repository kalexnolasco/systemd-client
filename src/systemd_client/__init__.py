"""systemd-client: High-level Python client for systemd user and system services."""

from systemd_client._version import __version__
from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import (
    ActiveState,
    BackendType,
    JournalPriority,
    LoadState,
    SubState,
    SystemdScope,
    UnitFileState,
    UnitType,
)
from systemd_client.exceptions import (
    BackendError,
    BackendNotAvailableError,
    JournalError,
    JournalParseError,
    SubprocessError,
    SystemdClientError,
    UnitNotFoundError,
    UnitOperationError,
)
from systemd_client.journal import AsyncJournalReader, JournalQuery, JournalReader
from systemd_client.models import EnableResult, JournalEntry, UnitFileInfo, UnitInfo, UnitStatus

__all__ = [
    "ActiveState",
    "AsyncJournalReader",
    "AsyncSystemdClient",
    "BackendError",
    "BackendNotAvailableError",
    "BackendType",
    "EnableResult",
    "JournalEntry",
    "JournalError",
    "JournalParseError",
    "JournalPriority",
    "JournalQuery",
    "JournalReader",
    "LoadState",
    "SubState",
    "SubprocessError",
    "SystemdClient",
    "SystemdClientError",
    "SystemdScope",
    "UnitFileInfo",
    "UnitFileState",
    "UnitInfo",
    "UnitNotFoundError",
    "UnitOperationError",
    "UnitStatus",
    "UnitType",
    "__version__",
]

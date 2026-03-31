"""systemd-client: High-level Python client for systemd user services."""

from systemd_client._version import __version__
from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import (
    ActiveState,
    BackendType,
    JournalPriority,
    LoadState,
    SubState,
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
from systemd_client.models import EnableResult, JournalEntry, UnitInfo, UnitStatus

__all__ = [
    # Version
    "__version__",
    # Clients
    "AsyncSystemdClient",
    "SystemdClient",
    # Enums
    "ActiveState",
    "BackendType",
    "JournalPriority",
    "LoadState",
    "SubState",
    "UnitFileState",
    "UnitType",
    # Exceptions
    "BackendError",
    "BackendNotAvailableError",
    "JournalError",
    "JournalParseError",
    "SubprocessError",
    "SystemdClientError",
    "UnitNotFoundError",
    "UnitOperationError",
    # Models
    "EnableResult",
    "JournalEntry",
    "UnitInfo",
    "UnitStatus",
    # Journal
    "AsyncJournalReader",
    "JournalQuery",
    "JournalReader",
]

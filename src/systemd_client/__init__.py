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
    # Enums
    "ActiveState",
    # Journal
    "AsyncJournalReader",
    # Clients
    "AsyncSystemdClient",
    # Exceptions
    "BackendError",
    "BackendNotAvailableError",
    "BackendType",
    # Models
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
    "UnitFileState",
    "UnitInfo",
    "UnitNotFoundError",
    "UnitOperationError",
    "UnitStatus",
    "UnitType",
    # Version
    "__version__",
]

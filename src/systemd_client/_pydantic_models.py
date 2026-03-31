"""Optional Pydantic BaseModel versions of the data models.

Only available when pydantic is installed:
    pip install systemd-client[pydantic]
"""

from __future__ import annotations

from datetime import datetime

try:
    from pydantic import BaseModel, ConfigDict
except ImportError as _exc:
    raise ImportError(
        "pydantic is required for Pydantic models. "
        "Install with: pip install systemd-client[pydantic]"
    ) from _exc

from systemd_client.enums import (
    ActiveState,
    JournalPriority,
    LoadState,
    SubState,
    UnitFileState,
)


class UnitInfoModel(BaseModel):
    """Pydantic model for unit summary information."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    load_state: LoadState
    active_state: ActiveState
    sub_state: SubState
    unit_file_state: UnitFileState | None = None


class UnitStatusModel(BaseModel):
    """Pydantic model for detailed unit status."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    load_state: LoadState
    active_state: ActiveState
    sub_state: SubState
    unit_file_state: UnitFileState | None = None
    fragment_path: str | None = None
    active_enter_timestamp: datetime | None = None
    active_exit_timestamp: datetime | None = None
    inactive_enter_timestamp: datetime | None = None
    inactive_exit_timestamp: datetime | None = None
    main_pid: int | None = None
    exec_main_status: int | None = None
    result: str | None = None
    triggered_by: list[str] = []
    documentation: list[str] = []
    properties: dict[str, str] = {}


class JournalEntryModel(BaseModel):
    """Pydantic model for a journal log entry."""

    model_config = ConfigDict(frozen=True)

    message: str
    priority: JournalPriority
    timestamp: datetime | None = None
    monotonic_timestamp: int | None = None
    unit: str | None = None
    syslog_identifier: str | None = None
    pid: int | None = None
    uid: int | None = None
    boot_id: str | None = None
    hostname: str | None = None
    cursor: str | None = None
    fields: dict[str, str] = {}


class EnableResultModel(BaseModel):
    """Pydantic model for enable/disable operation results."""

    model_config = ConfigDict(frozen=True)

    changes: list[tuple[str, str, str]] = []
    carries_install_info: bool = False

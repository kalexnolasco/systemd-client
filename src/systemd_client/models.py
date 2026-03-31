"""Data models for systemd-client (frozen dataclasses with slots)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from systemd_client.enums import (
        ActiveState,
        JournalPriority,
        LoadState,
        SubState,
        UnitFileState,
    )


@dataclass(frozen=True, slots=True)
class UnitInfo:
    """Summary information about a systemd unit (from list-units)."""

    name: str
    description: str
    load_state: LoadState
    active_state: ActiveState
    sub_state: SubState
    unit_file_state: UnitFileState | None = None


@dataclass(frozen=True, slots=True)
class UnitStatus:
    """Detailed status of a systemd unit (from show/status)."""

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
    triggered_by: list[str] = field(default_factory=list)
    documentation: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """A single journal log entry."""

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
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EnableResult:
    """Result of enable/disable/mask/unmask operations."""

    changes: list[tuple[str, str, str]] = field(default_factory=list)
    carries_install_info: bool = False

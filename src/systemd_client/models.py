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
        UnitType,
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
class UnitFileInfo:
    """Information about an installed unit file (from list-unit-files)."""

    name: str
    state: UnitFileState
    preset: str | None = None


@dataclass(frozen=True, slots=True)
class UnitFile:
    """A generated systemd unit file."""

    name: str
    content: str
    unit_type: UnitType


@dataclass(frozen=True, slots=True)
class SessionInfo:
    """Information about a login session (from loginctl)."""

    id: str
    uid: int
    user: str
    seat: str = ""
    tty: str = ""
    state: str = ""


@dataclass(frozen=True, slots=True)
class UserInfo:
    """Information about a logged-in user (from loginctl)."""

    uid: int
    name: str
    state: str = ""


@dataclass(frozen=True, slots=True)
class BlameEntry:
    """A single entry from systemd-analyze blame."""

    time_us: int
    unit: str


@dataclass(frozen=True, slots=True)
class SecurityIssue:
    """A single security issue from systemd-analyze security."""

    id: str
    description: str
    severity: str
    value: str


@dataclass(frozen=True, slots=True)
class SecurityAnalysis:
    """Result of systemd-analyze security for a unit."""

    unit: str
    exposure: float
    issues: list[SecurityIssue] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """Resource usage information for a unit."""

    cpu_usage_nsec: int | None = None
    memory_current: int | None = None
    memory_peak: int | None = None
    tasks_current: int | None = None
    io_read_bytes: int | None = None
    io_write_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class TimerInfo:
    """Information about an active timer."""

    name: str
    next_trigger: datetime | None = None
    time_left: str | None = None
    last_trigger: datetime | None = None
    unit: str | None = None
    activates: str | None = None


@dataclass(frozen=True, slots=True)
class SocketInfo:
    """Information about an active socket."""

    name: str
    listen: str = ""
    type: str = ""
    unit: str = ""


@dataclass(frozen=True, slots=True)
class TransientResult:
    """Result of running a transient unit via systemd-run."""

    unit_name: str
    pid: int | None = None


@dataclass(frozen=True, slots=True)
class EnableResult:
    """Result of enable/disable/mask/unmask operations."""

    changes: list[tuple[str, str, str]] = field(default_factory=list)
    carries_install_info: bool = False

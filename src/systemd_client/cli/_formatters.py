"""Output formatting for CLI: table and JSON modes."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systemd_client.models import JournalEntry, UnitFileInfo, UnitInfo, UnitStatus


def _serialize(obj: object) -> object:
    """JSON serializer for dataclass fields."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def format_units_table(units: list[UnitInfo], no_color: bool = False) -> str:
    """Format unit list as a table."""
    if not units:
        return "No units found."

    # Column widths
    name_w = max(len(u.name) for u in units)
    load_w = max(len(u.load_state.value) for u in units)
    active_w = max(len(u.active_state.value) for u in units)
    sub_w = max(len(u.sub_state.value) for u in units)

    header = (
        f"{'UNIT':<{name_w}}  {'LOAD':<{load_w}}  "
        f"{'ACTIVE':<{active_w}}  {'SUB':<{sub_w}}  DESCRIPTION"
    )
    lines = [header]

    for u in units:
        active_str = u.active_state.value
        if not no_color:
            if u.active_state.value == "active":
                active_str = f"\033[32m{active_str}\033[0m"
            elif u.active_state.value == "failed":
                active_str = f"\033[31m{active_str}\033[0m"
            elif u.active_state.value == "inactive":
                active_str = f"\033[90m{active_str}\033[0m"

        # Pad after ANSI codes if used
        if not no_color and u.active_state.value in ("active", "failed", "inactive"):
            pad = active_w - len(u.active_state.value)
            active_col = active_str + " " * pad
        else:
            active_col = f"{active_str:<{active_w}}"

        line = (
            f"{u.name:<{name_w}}  {u.load_state.value:<{load_w}}  "
            f"{active_col}  {u.sub_state.value:<{sub_w}}  {u.description}"
        )
        lines.append(line)

    return "\n".join(lines)


def format_units_json(units: list[UnitInfo]) -> str:
    """Format unit list as JSON."""
    return json.dumps([asdict(u) for u in units], default=_serialize, indent=2)


def format_unit_files_table(files: list[UnitFileInfo], no_color: bool = False) -> str:
    """Format unit file list as a table."""
    if not files:
        return "No unit files found."

    name_w = max(len(f.name) for f in files)
    state_w = max(len(f.state.value) for f in files)

    header = f"{'UNIT FILE':<{name_w}}  {'STATE':<{state_w}}  PRESET"
    lines = [header]

    for f in files:
        state_str = f.state.value
        if not no_color:
            if f.state.value == "enabled":
                state_str = f"\033[32m{state_str}\033[0m"
            elif f.state.value in ("disabled", "masked"):
                state_str = f"\033[90m{state_str}\033[0m"
            elif f.state.value == "static":
                state_str = f"\033[33m{state_str}\033[0m"

        if not no_color and f.state.value in ("enabled", "disabled", "masked", "static"):
            pad = state_w - len(f.state.value)
            state_col = state_str + " " * pad
        else:
            state_col = f"{state_str:<{state_w}}"

        preset = f.preset or "-"
        line = f"{f.name:<{name_w}}  {state_col}  {preset}"
        lines.append(line)

    return "\n".join(lines)


def format_unit_files_json(files: list[UnitFileInfo]) -> str:
    """Format unit file list as JSON."""
    return json.dumps([asdict(f) for f in files], default=_serialize, indent=2)


def format_status_table(status: UnitStatus, no_color: bool = False) -> str:
    """Format unit status as a human-readable block."""
    lines: list[str] = []

    # Active state coloring
    active_str = f"{status.active_state.value} ({status.sub_state.value})"
    if not no_color:
        if status.active_state.value == "active":
            active_str = f"\033[32m{active_str}\033[0m"
        elif status.active_state.value == "failed":
            active_str = f"\033[31m{active_str}\033[0m"

    lines.append(f"  Unit: {status.name}")
    if status.description:
        lines.append(f"  Description: {status.description}")
    lines.append(f"  Loaded: {status.load_state.value}")
    lines.append(f"  Active: {active_str}")
    if status.main_pid:
        lines.append(f"  Main PID: {status.main_pid}")
    if status.fragment_path:
        lines.append(f"  Unit file: {status.fragment_path}")
    if status.exec_main_status is not None:
        lines.append(f"  Exit code: {status.exec_main_status}")
    if status.result and status.result != "success":
        lines.append(f"  Result: {status.result}")
    if status.documentation:
        lines.append(f"  Docs: {', '.join(status.documentation)}")

    return "\n".join(lines)


def format_status_json(status: UnitStatus) -> str:
    """Format unit status as JSON."""
    return json.dumps(asdict(status), default=_serialize, indent=2)


def format_journal_table(entries: list[JournalEntry], no_color: bool = False) -> str:
    """Format journal entries as human-readable lines."""
    if not entries:
        return "No journal entries."

    lines: list[str] = []
    for e in entries:
        ts = e.timestamp.strftime("%b %d %H:%M:%S") if e.timestamp else "                "
        host = e.hostname or ""
        ident = e.syslog_identifier or ""
        pid_str = f"[{e.pid}]" if e.pid else ""

        prefix = f"{ts} {host} {ident}{pid_str}: "
        msg = e.message

        if not no_color:
            if e.priority.value <= "3":  # ERR and above
                msg = f"\033[31m{msg}\033[0m"
            elif e.priority.value == "4":  # WARNING
                msg = f"\033[33m{msg}\033[0m"

        lines.append(f"{prefix}{msg}")

    return "\n".join(lines)


def format_journal_json(entries: list[JournalEntry]) -> str:
    """Format journal entries as JSON."""
    return json.dumps([asdict(e) for e in entries], default=_serialize, indent=2)

"""JSON line parsing and field normalization for journal entries."""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime

from systemd_client.enums import JournalPriority
from systemd_client.exceptions import JournalParseError
from systemd_client.models import JournalEntry


def parse_journal_line(line: str) -> JournalEntry:
    """Parse a single JSON line from journalctl --output=json."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise JournalParseError(f"Invalid JSON: {line[:200]}") from exc

    return _entry_from_dict(data)


def _entry_from_dict(data: dict[str, object]) -> JournalEntry:
    """Build a JournalEntry from a parsed JSON dict."""
    message = str(data.get("MESSAGE", ""))

    # Priority
    raw_priority = str(data.get("PRIORITY", "6"))
    try:
        priority = JournalPriority(raw_priority)
    except ValueError:
        priority = JournalPriority.INFO

    # Timestamp from __REALTIME_TIMESTAMP (microseconds since epoch)
    timestamp: datetime | None = None
    raw_ts = data.get("__REALTIME_TIMESTAMP")
    if raw_ts is not None:
        with contextlib.suppress(ValueError, OSError, TypeError):
            timestamp = datetime.fromtimestamp(int(raw_ts) / 1_000_000, tz=UTC)

    # Monotonic timestamp
    monotonic: int | None = None
    raw_mono = data.get("__MONOTONIC_TIMESTAMP")
    if raw_mono is not None:
        with contextlib.suppress(ValueError, TypeError):
            monotonic = int(raw_mono)

    # Integer fields
    def _safe_int(key: str) -> int | None:
        raw = data.get(key)
        if raw is None:
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    # Collect all extra fields
    known_keys = {
        "MESSAGE", "PRIORITY", "__REALTIME_TIMESTAMP", "__MONOTONIC_TIMESTAMP",
        "_SYSTEMD_UNIT", "SYSLOG_IDENTIFIER", "_PID", "_UID",
        "_BOOT_ID", "_HOSTNAME", "__CURSOR",
    }
    fields = {str(k): str(v) for k, v in data.items() if k not in known_keys}

    return JournalEntry(
        message=message,
        priority=priority,
        timestamp=timestamp,
        monotonic_timestamp=monotonic,
        unit=str(data.get("_SYSTEMD_UNIT", "")) or None,
        syslog_identifier=str(data.get("SYSLOG_IDENTIFIER", "")) or None,
        pid=_safe_int("_PID"),
        uid=_safe_int("_UID"),
        boot_id=str(data.get("_BOOT_ID", "")) or None,
        hostname=str(data.get("_HOSTNAME", "")) or None,
        cursor=str(data.get("__CURSOR", "")) or None,
        fields=fields,
    )

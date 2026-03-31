#!/usr/bin/env python3
"""Query journal entries for a service.

Usage:
    python examples/05_journal_query.py
    python examples/05_journal_query.py my-app.service
    python examples/05_journal_query.py my-app.service 50
"""

import sys

from systemd_client import SystemdClient, JournalPriority

unit = sys.argv[1] if len(sys.argv) > 1 else None
lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20

client = SystemdClient()

# Basic query: last N lines
entries = client.journal(unit=unit, lines=lines)

for entry in entries:
    ts = entry.timestamp.strftime("%b %d %H:%M:%S") if entry.timestamp else "                "
    ident = entry.syslog_identifier or ""
    pid = f"[{entry.pid}]" if entry.pid else ""
    print(f"{ts} {ident}{pid}: {entry.message}")

print(f"\n--- {len(entries)} entries ---")

# Query with priority filter (warnings and above)
print("\n=== Warnings and above (last hour) ===\n")

warnings = client.journal(
    unit=unit,
    priority=JournalPriority.WARNING,
    since="1h ago",
    lines=10,
)

for entry in warnings:
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"[{entry.priority.name}] {ts} {entry.message}")

if not warnings:
    print("(none)")

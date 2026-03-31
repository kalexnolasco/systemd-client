#!/usr/bin/env python3
"""Search journal entries by regex pattern.

Usage:
    python examples/11_journal_grep.py <pattern>
    python examples/11_journal_grep.py <pattern> <unit>
    python examples/11_journal_grep.py "error|fail" my-app.service
    python examples/11_journal_grep.py "timeout"
"""

import sys

from systemd_client import SystemdClient

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <pattern> [unit]")
    sys.exit(1)

pattern = sys.argv[1]
unit = sys.argv[2] if len(sys.argv) > 2 else None

client = SystemdClient()

entries = client.journal(
    unit=unit,
    grep=pattern,
    lines=50,
    since="24h ago",
)

print(f"Searching for '{pattern}'{f' in {unit}' if unit else ''} (last 24h):\n")

for entry in entries:
    ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else ""
    ident = entry.syslog_identifier or ""
    print(f"  {ts} [{entry.priority.name:<7}] {ident}: {entry.message[:120]}")

print(f"\n--- {len(entries)} matches ---")

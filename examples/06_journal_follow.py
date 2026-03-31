#!/usr/bin/env python3
"""Follow journal output in real-time (like journalctl -f).

Press Ctrl+C to stop.

Usage:
    python examples/06_journal_follow.py
    python examples/06_journal_follow.py my-app.service
"""

import sys

from systemd_client import SystemdClient

unit = sys.argv[1] if len(sys.argv) > 1 else None

client = SystemdClient()

print(f"Following journal{f' for {unit}' if unit else ''}... (Ctrl+C to stop)\n")

try:
    for entry in client.journal_follow(unit=unit, lines=10):
        ts = entry.timestamp.strftime("%b %d %H:%M:%S") if entry.timestamp else ""
        ident = entry.syslog_identifier or ""
        pid = f"[{entry.pid}]" if entry.pid else ""
        print(f"{ts} {ident}{pid}: {entry.message}")
except KeyboardInterrupt:
    print("\nStopped.")

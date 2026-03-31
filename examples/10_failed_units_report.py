#!/usr/bin/env python3
"""Report all failed user units with their recent journal errors.

Usage:
    python examples/10_failed_units_report.py
"""

from systemd_client import SystemdClient, JournalPriority

client = SystemdClient()

# Find all failed units
all_units = client.list_units()
failed = [u for u in all_units if u.active_state == "failed"]

if not failed:
    print("No failed units. Everything is healthy!")
    raise SystemExit(0)

print(f"Found {len(failed)} failed unit(s):\n")

for unit in failed:
    print(f"  FAILED: {unit.name}")
    print(f"          {unit.description}")

    # Get recent error logs for this unit
    errors = client.journal(
        unit=unit.name,
        priority=JournalPriority.ERR,
        lines=5,
    )

    if errors:
        print("          Recent errors:")
        for entry in errors:
            ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else ""
            print(f"            {ts} {entry.message[:100]}")
    print()

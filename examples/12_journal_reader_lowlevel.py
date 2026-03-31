#!/usr/bin/env python3
"""Low-level journal access using JournalReader and JournalQuery directly.

Useful when you need fine-grained control over query parameters.

Usage:
    python examples/12_journal_reader_lowlevel.py
"""

from systemd_client import JournalPriority, JournalReader
from systemd_client.journal import JournalQuery

reader = JournalReader()

# Complex query with multiple filters
query = JournalQuery(
    unit="my-app.service",
    priority=JournalPriority.WARNING,
    lines=20,
    since="2h ago",
    reverse=True,  # newest first
)

print(f"journalctl args: {' '.join(query.to_args())}\n")

entries = reader.query(query)

for entry in entries:
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"  {ts} [{entry.priority.name}] {entry.message}")

    # Access raw journal fields
    if entry.fields.get("_SYSTEMD_CGROUP"):
        print(f"         cgroup: {entry.fields['_SYSTEMD_CGROUP']}")

print(f"\n--- {len(entries)} entries ---")

# Query by syslog identifier
print("\n=== By syslog identifier ===\n")

query2 = JournalQuery(
    identifiers=["sshd", "sudo"],
    lines=10,
    since="1h ago",
)

for entry in reader.query(query2):
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"  {ts} {entry.syslog_identifier}: {entry.message}")

#!/usr/bin/env python3
"""Monitor resource usage of services.

Shows CPU, memory, and I/O stats; applies runtime resource limits;
and lists active timers.

Usage:
    python examples/19_resource_monitor.py <unit-name>
    python examples/19_resource_monitor.py my-app.service
"""

import sys

from systemd_client import SystemdClient

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <unit-name>")
    sys.exit(1)

unit_name = sys.argv[1]
client = SystemdClient()

# -- Resource usage --
print(f"Resource usage for {unit_name}:")
print("-" * 50)

usage = client.get_resource_usage(unit_name)

if usage.cpu_usage_nsec is not None:
    cpu_sec = usage.cpu_usage_nsec / 1_000_000_000
    print(f"  CPU time:      {cpu_sec:.2f}s")

if usage.memory_current is not None:
    mem_mb = usage.memory_current / (1024 * 1024)
    print(f"  Memory (cur):  {mem_mb:.1f} MB")

if usage.memory_peak is not None:
    peak_mb = usage.memory_peak / (1024 * 1024)
    print(f"  Memory (peak): {peak_mb:.1f} MB")

if usage.tasks_current is not None:
    print(f"  Tasks:         {usage.tasks_current}")

if usage.io_read_bytes is not None:
    io_read_mb = usage.io_read_bytes / (1024 * 1024)
    print(f"  I/O read:      {io_read_mb:.1f} MB")

if usage.io_write_bytes is not None:
    io_write_mb = usage.io_write_bytes / (1024 * 1024)
    print(f"  I/O write:     {io_write_mb:.1f} MB")

# -- Apply a runtime memory limit --
print(f"\nApplying MemoryMax=512M to {unit_name}...")
client.set_property(unit_name, {"MemoryMax": "512M"})
print("  Done (runtime only, not persisted)")

# -- List all active timers --
print("\nActive timers:")
print(f"  {'TIMER':<35} {'NEXT TRIGGER':<28} {'TIME LEFT'}")
print("  " + "-" * 85)

timers = client.list_timers()
for t in timers:
    next_str = str(t.next_trigger) if t.next_trigger else "n/a"
    left_str = t.time_left or "n/a"
    print(f"  {t.name:<35} {next_str:<28} {left_str}")

if not timers:
    print("  (none)")

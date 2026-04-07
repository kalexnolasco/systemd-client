#!/usr/bin/env python3
"""Run commands as transient systemd services.

Transient units are created on the fly with systemd-run, no unit file
needed. They are cleaned up automatically when the process exits.

Usage:
    python examples/18_transient_run.py
"""

from systemd_client import SystemdClient

client = SystemdClient()

# -- Example 1: Run a one-off command --
print("=== One-off command ===")
result = client.run(
    "/usr/bin/echo hello from systemd",
    name="my-echo-job",
    wait=True,               # block until the command finishes
    remain_after_exit=False,  # remove the unit after exit
)
print(f"Transient unit: {result.unit_name}")
if result.pid:
    print(f"PID:            {result.pid}")

# -- Example 2: Run with resource limits --
print("\n=== Command with resource limits ===")
result = client.run(
    ["/usr/bin/stress-ng", "--cpu", "1", "--timeout", "5"],
    name="limited-stress",
    wait=True,
    properties={
        "MemoryMax": "256M",
        "CPUQuota": "50%",
    },
)
print(f"Transient unit: {result.unit_name}")

# -- Example 3: Schedule a command on a calendar --
print("\n=== Scheduled transient timer ===")
result = client.run_on_calendar(
    on_calendar="*:0/30",                       # every 30 minutes
    command="/usr/local/bin/cleanup-temp.sh",
    name="temp-cleanup",
)
print(f"Transient timer: {result.unit_name}")
print("(will run every 30 minutes until stopped)")

# To stop a transient timer:
#   client.stop("temp-cleanup.timer")

#!/usr/bin/env python3
"""Complete deploy workflow: create, install, start, monitor, journal.

Demonstrates the full lifecycle of a service managed entirely from
Python: build the unit file, install it, start it, check resources,
read journal logs, and tear it down.

Usage:
    python examples/22_full_deploy.py
"""

import time

from systemd_client import (
    JournalPriority,
    ServiceBuilder,
    SystemdClient,
    UnitOperationError,
)

SERVICE_NAME = "demo-deploy"
client = SystemdClient()

# ── Step 1: Build the unit file ────────────────────────────────
print("[1/7] Building unit file...")

unit_file = (
    ServiceBuilder(SERVICE_NAME)
    .description("Demo service for full deploy example")
    .type_("simple")
    .exec_start("/usr/bin/python3 -c \"import time; [time.sleep(1) for _ in range(300)]\"")
    .restart("on-failure")
    .restart_sec(3)
    .standard_output("journal")
    .standard_error("journal")
    .syslog_identifier(SERVICE_NAME)
    .wanted_by("default.target")
    .build()
)
print(f"       Generated {unit_file.name}")

# ── Step 2: Install ────────────────────────────────────────────
print("[2/7] Installing unit file...")
path = client.install(unit_file)
print(f"       Installed to {path}")

# ── Step 3: Enable + start ─────────────────────────────────────
print(f"[3/7] Enabling and starting {SERVICE_NAME}.service...")
client.enable(f"{SERVICE_NAME}.service")
client.start(f"{SERVICE_NAME}.service")
time.sleep(2)  # let the service stabilize

# ── Step 4: Verify status ──────────────────────────────────────
print("[4/7] Checking status...")
status = client.status(f"{SERVICE_NAME}.service")
print(f"       State: {status.active_state} ({status.sub_state})")
if status.main_pid:
    print(f"       PID:   {status.main_pid}")

if client.is_failed(f"{SERVICE_NAME}.service"):
    print("       SERVICE FAILED -- aborting")
    entries = client.journal(unit=f"{SERVICE_NAME}.service", lines=5)
    for e in entries:
        print(f"       > {e.message}")
    client.uninstall(f"{SERVICE_NAME}.service")
    raise SystemExit(1)

# ── Step 5: Resource usage ─────────────────────────────────────
print("[5/7] Checking resource usage...")
usage = client.get_resource_usage(f"{SERVICE_NAME}.service")
if usage.memory_current is not None:
    mem_mb = usage.memory_current / (1024 * 1024)
    print(f"       Memory: {mem_mb:.1f} MB")
if usage.cpu_usage_nsec is not None:
    cpu_ms = usage.cpu_usage_nsec / 1_000_000
    print(f"       CPU:    {cpu_ms:.1f} ms")

# ── Step 6: Read journal logs ──────────────────────────────────
print("[6/7] Reading journal logs...")
entries = client.journal(
    unit=f"{SERVICE_NAME}.service",
    lines=10,
    priority=JournalPriority.INFO,
)
for entry in entries:
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "??:??:??"
    print(f"       {ts} [{entry.priority.name}] {entry.message}")
if not entries:
    print("       (no journal entries yet)")

# ── Step 7: Tear down ─────────────────────────────────────────
print(f"[7/7] Stopping and removing {SERVICE_NAME}.service...")
try:
    client.stop(f"{SERVICE_NAME}.service")
except UnitOperationError:
    pass  # may already be stopped

client.disable(f"{SERVICE_NAME}.service")
client.uninstall(f"{SERVICE_NAME}.service")
print("       Removed.\n")

print("Full deploy lifecycle complete.")

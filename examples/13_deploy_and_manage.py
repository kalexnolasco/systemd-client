#!/usr/bin/env python3
"""Deploy workflow: reload daemon, restart service, verify it's running.

Typical pattern after updating a unit file or deploying new code.

Usage:
    python examples/13_deploy_and_manage.py <unit-name>
    python examples/13_deploy_and_manage.py my-app.service
"""

import sys
import time

from systemd_client import SystemdClient, UnitOperationError

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <unit-name>")
    sys.exit(1)

unit_name = sys.argv[1]
client = SystemdClient()

print(f"Deploying {unit_name}...\n")

# Step 1: Reload daemon (picks up unit file changes)
print("  [1/4] Reloading daemon...")
client.daemon_reload()
print("        OK")

# Step 2: Restart the service
print(f"  [2/4] Restarting {unit_name}...")
try:
    client.restart(unit_name)
    print("        OK")
except UnitOperationError as e:
    print(f"        FAILED: {e}")
    sys.exit(1)

# Step 3: Wait a moment and verify
print("  [3/4] Waiting for service to stabilize...")
time.sleep(2)

is_active = client.is_active(unit_name)
is_failed = client.is_failed(unit_name)

if is_failed:
    print("        FAILED!")
    status = client.status(unit_name)
    print(f"        Result: {status.result}")

    # Show recent errors
    errors = client.journal(unit=unit_name, lines=5)
    for e in errors:
        print(f"        > {e.message}")
    sys.exit(1)

if not is_active:
    print("        NOT ACTIVE (may still be starting)")
else:
    print("        OK - service is active")

# Step 4: Show status summary
print(f"  [4/4] Status summary:")
status = client.status(unit_name)
print(f"        State:  {status.active_state} ({status.sub_state})")
if status.main_pid:
    print(f"        PID:    {status.main_pid}")

print(f"\nDeploy complete.")

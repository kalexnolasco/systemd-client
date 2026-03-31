#!/usr/bin/env python3
"""Batch operations: restart multiple services at once.

Usage:
    python examples/14_batch_operations.py restart service1.service service2.service
    python examples/14_batch_operations.py stop service1.service service2.service
"""

import sys

from systemd_client import SystemdClient, UnitOperationError

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <start|stop|restart> <unit1> [unit2] ...")
    sys.exit(1)

action = sys.argv[1]
unit_names = sys.argv[2:]

if action not in ("start", "stop", "restart"):
    print(f"Invalid action: {action}")
    sys.exit(1)

client = SystemdClient()
errors = []

for unit_name in unit_names:
    try:
        getattr(client, action)(unit_name)
        is_active = client.is_active(unit_name)
        status = "active" if is_active else "inactive"
        print(f"  [ OK ] {action} {unit_name} -> {status}")
    except UnitOperationError as e:
        errors.append((unit_name, str(e)))
        print(f"  [FAIL] {action} {unit_name}: {e.detail}")

print()
if errors:
    print(f"{len(errors)} error(s) occurred:")
    for unit, err in errors:
        print(f"  - {unit}: {err}")
    sys.exit(1)
else:
    print(f"All {len(unit_names)} units {action}ed successfully.")

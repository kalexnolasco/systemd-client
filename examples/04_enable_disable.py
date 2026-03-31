#!/usr/bin/env python3
"""Enable or disable a user service.

Usage:
    python examples/04_enable_disable.py <unit-name> <enable|disable>
    python examples/04_enable_disable.py my-app.service enable
"""

import sys

from systemd_client import SystemdClient, UnitOperationError

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <unit-name> <enable|disable|mask|unmask>")
    sys.exit(1)

unit_name = sys.argv[1]
action = sys.argv[2]

if action not in ("enable", "disable", "mask", "unmask"):
    print(f"Invalid action: {action}. Use: enable, disable, mask, unmask")
    sys.exit(1)

client = SystemdClient()

try:
    result = getattr(client, action)(unit_name)
    print(f"OK: {action} {unit_name}")

    if result.changes:
        print("Changes:")
        for change in result.changes:
            print(f"  {change[0]} {change[1]} {change[2]}".rstrip())

    # Show current state
    is_enabled = client.is_enabled(unit_name)
    print(f"Enabled: {is_enabled}")

except UnitOperationError as e:
    print(f"Failed: {e}")
    sys.exit(1)

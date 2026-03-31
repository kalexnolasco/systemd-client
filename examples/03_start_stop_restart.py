#!/usr/bin/env python3
"""Start, stop, and restart a user service.

Usage:
    python examples/03_start_stop_restart.py <unit-name> <action>
    python examples/03_start_stop_restart.py my-app.service start
    python examples/03_start_stop_restart.py my-app.service restart
"""

import sys

from systemd_client import SystemdClient, UnitNotFoundError, UnitOperationError

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <unit-name> <start|stop|restart|reload>")
    sys.exit(1)

unit_name = sys.argv[1]
action = sys.argv[2]

if action not in ("start", "stop", "restart", "reload"):
    print(f"Invalid action: {action}. Use: start, stop, restart, reload")
    sys.exit(1)

client = SystemdClient()

try:
    getattr(client, action)(unit_name)
    print(f"OK: {action} {unit_name}")

    # Show new state
    is_active = client.is_active(unit_name)
    print(f"Active: {is_active}")

except UnitNotFoundError:
    print(f"Unit not found: {unit_name}")
    sys.exit(1)
except UnitOperationError as e:
    print(f"Failed: {e}")
    sys.exit(1)

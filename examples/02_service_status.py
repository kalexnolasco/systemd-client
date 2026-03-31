#!/usr/bin/env python3
"""Show detailed status of a specific service.

Usage:
    python examples/02_service_status.py <unit-name>
    python examples/02_service_status.py pipewire.service
"""

import sys

from systemd_client import SystemdClient, UnitNotFoundError

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <unit-name>")
    sys.exit(1)

unit_name = sys.argv[1]
client = SystemdClient()

try:
    status = client.status(unit_name)
except UnitNotFoundError:
    print(f"Unit not found: {unit_name}")
    sys.exit(1)

print(f"  Unit:        {status.name}")
print(f"  Description: {status.description}")
print(f"  Load:        {status.load_state}")
print(f"  Active:      {status.active_state} ({status.sub_state})")

if status.main_pid:
    print(f"  Main PID:    {status.main_pid}")
if status.fragment_path:
    print(f"  Unit file:   {status.fragment_path}")
if status.active_enter_timestamp:
    print(f"  Since:       {status.active_enter_timestamp}")
if status.result and status.result != "success":
    print(f"  Result:      {status.result}")
if status.documentation:
    print(f"  Docs:        {', '.join(status.documentation)}")

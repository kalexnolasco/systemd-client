#!/usr/bin/env python3
"""Health check: verify a list of services are running.

Exits with code 0 if all are active, 1 if any are not.

Usage:
    python examples/09_health_check.py service1.service service2.service ...
    python examples/09_health_check.py pipewire.service wireplumber.service
"""

import sys

from systemd_client import SystemdClient

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <unit1> [unit2] [unit3] ...")
    sys.exit(1)

units_to_check = sys.argv[1:]
client = SystemdClient()

all_ok = True

for unit_name in units_to_check:
    active = client.is_active(unit_name)
    failed = client.is_failed(unit_name)

    if failed:
        symbol = "FAIL"
        all_ok = False
    elif active:
        symbol = " OK "
    else:
        symbol = "DOWN"
        all_ok = False

    print(f"  [{symbol}] {unit_name}")

print()
if all_ok:
    print("All services healthy.")
    sys.exit(0)
else:
    print("Some services are not running!")
    sys.exit(1)

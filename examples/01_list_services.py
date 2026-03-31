#!/usr/bin/env python3
"""List all user services and their states.

Usage:
    python examples/01_list_services.py
"""

from systemd_client import SystemdClient

client = SystemdClient()

# List only services
services = client.list_units(unit_type="service")

print(f"{'UNIT':<40} {'ACTIVE':<12} {'SUB':<12} DESCRIPTION")
print("-" * 90)

for svc in services:
    print(f"{svc.name:<40} {svc.active_state:<12} {svc.sub_state:<12} {svc.description}")

print(f"\nTotal: {len(services)} services")

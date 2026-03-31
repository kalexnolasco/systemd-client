#!/usr/bin/env python3
"""Async client usage — list services and read journal concurrently.

Usage:
    python examples/07_async_client.py
"""

import asyncio

from systemd_client import AsyncSystemdClient


async def main():
    client = AsyncSystemdClient()

    # Run both queries concurrently
    units, journal = await asyncio.gather(
        client.list_units(unit_type="service"),
        client.journal(lines=10),
    )

    print("=== Active Services ===\n")
    active = [u for u in units if u.active_state == "active"]
    for svc in active[:10]:
        print(f"  {svc.name:<40} {svc.sub_state}")
    print(f"  ... {len(active)} active services total")

    print("\n=== Last 10 Journal Entries ===\n")
    for entry in journal:
        ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
        print(f"  {ts} [{entry.priority.name:<7}] {entry.message[:80]}")


asyncio.run(main())

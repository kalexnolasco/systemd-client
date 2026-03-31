#!/usr/bin/env python3
"""Async monitoring: poll service status every N seconds.

Simple dashboard that refreshes in the terminal.
Press Ctrl+C to stop.

Usage:
    python examples/15_async_monitor_dashboard.py service1.service service2.service
"""

import asyncio
import os
import sys

from systemd_client import AsyncSystemdClient


async def check_unit(client: AsyncSystemdClient, unit_name: str) -> str:
    """Check a single unit and return a formatted status line."""
    try:
        status = await client.status(unit_name)
        state = f"{status.active_state} ({status.sub_state})"
        pid = f"PID {status.main_pid}" if status.main_pid else ""
        return f"  {unit_name:<40} {state:<25} {pid}"
    except Exception as e:
        return f"  {unit_name:<40} {'ERROR':<25} {e}"


async def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <unit1> [unit2] ...")
        return

    unit_names = sys.argv[1:]
    client = AsyncSystemdClient()
    interval = 5  # seconds

    print(f"Monitoring {len(unit_names)} unit(s) every {interval}s (Ctrl+C to stop)\n")

    while True:
        # Check all units concurrently
        results = await asyncio.gather(
            *(check_unit(client, name) for name in unit_names)
        )

        # Clear screen and print
        os.system("clear" if os.name == "posix" else "cls")
        print(f"{'UNIT':<42} {'STATE':<25} {'INFO'}")
        print("-" * 80)
        for line in results:
            print(line)
        print(f"\nRefreshing every {interval}s... (Ctrl+C to stop)")

        await asyncio.sleep(interval)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nStopped.")

#!/usr/bin/env python3
"""Async journal follow — non-blocking real-time log stream.

Press Ctrl+C to stop.

Usage:
    python examples/08_async_follow.py
    python examples/08_async_follow.py my-app.service
"""

import asyncio
import sys

from systemd_client import AsyncSystemdClient


async def main():
    unit = sys.argv[1] if len(sys.argv) > 1 else None

    client = AsyncSystemdClient()

    print(f"Following journal{f' for {unit}' if unit else ''}... (Ctrl+C to stop)\n")

    async for entry in client.journal_follow(unit=unit, lines=5):
        ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
        ident = entry.syslog_identifier or ""
        print(f"{ts} {ident}: {entry.message}")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nStopped.")

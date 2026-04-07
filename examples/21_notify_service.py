#!/usr/bin/env python3
"""Python service with sd_notify integration.

Shows how to use SystemdNotifier to communicate lifecycle events back
to systemd. This script is meant to be run as a Type=notify service:

    [Service]
    Type=notify
    WatchdogSec=30
    ExecStart=/usr/bin/python3 /path/to/21_notify_service.py

Usage (standalone test, $NOTIFY_SOCKET will be unset):
    python examples/21_notify_service.py
"""

import signal
import sys
import time

from systemd_client import SystemdNotifier

notifier = SystemdNotifier()
running = True


def handle_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global running
    print("Received shutdown signal")
    notifier.stopping()
    running = False


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# -- Startup phase --
print("Initializing...")
if not notifier.available:
    print("  (NOTIFY_SOCKET not set -- running outside systemd)")

time.sleep(1)  # simulate startup work

# Tell systemd we are ready
notifier.ready()
notifier.status("Listening on :8080")
print("Service ready")

# -- Main loop with watchdog --
counter = 0
while running:
    counter += 1
    notifier.status(f"Processed {counter} requests")
    notifier.watchdog()  # keep-alive ping

    # Simulate work
    time.sleep(5)

# -- Shutdown --
notifier.status("Shutting down...")
print("Cleanup complete")
notifier.close()
sys.exit(0)

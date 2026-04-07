#!/usr/bin/env python3
"""Create a daily backup timer.

Builds a matching service + timer pair: the timer triggers the service
on a calendar schedule. Both are installed and enabled together.

Usage:
    python examples/17_create_timer.py
"""

from systemd_client import ServiceBuilder, SystemdClient, TimerBuilder

client = SystemdClient()

# Build the service that performs the backup
service = (
    ServiceBuilder("daily-backup")
    .description("Daily backup to remote storage")
    .type_("oneshot")
    .exec_start("/usr/local/bin/backup.sh")
    .environment({"BACKUP_DEST": "/mnt/backups", "RETENTION_DAYS": "30"})
    .standard_output("journal")
    .standard_error("journal")
    .build()
)

# Build the timer that triggers the service
timer = (
    TimerBuilder("daily-backup")
    .description("Run daily backup at 02:00")
    .on_calendar("*-*-* 02:00:00")   # every day at 2 AM
    .persistent(True)                 # catch up if system was off
    .accuracy_sec(300)                # allow 5-minute window
    .randomized_delay_sec(600)        # spread load by up to 10 minutes
    .wanted_by("timers.target")
    .build()
)

# Preview both unit files
for uf in (service, timer):
    print(f"--- {uf.name} ---")
    print(uf.content)

# Install both unit files
svc_path = client.install(service)
tmr_path = client.install(timer)
print(f"Installed service: {svc_path}")
print(f"Installed timer:   {tmr_path}")

# Enable and start the timer (not the service -- the timer activates it)
client.enable("daily-backup.timer")
client.start("daily-backup.timer")

# Verify the timer is scheduled
timers = client.list_timers()
for t in timers:
    if t.name == "daily-backup.timer":
        print(f"\nTimer active: next trigger = {t.next_trigger}")
        print(f"              time left   = {t.time_left}")
        break
else:
    print("\nTimer is registered (check with: systemctl --user list-timers)")

#!/usr/bin/env python3
"""Create and deploy a systemd service from Python.

Uses ServiceBuilder to define a unit file, then installs, enables,
and starts it through the client.

Usage:
    python examples/16_create_service.py
"""

from systemd_client import ServiceBuilder, SystemdClient

client = SystemdClient()

# Build a service unit file using the fluent API
unit_file = (
    ServiceBuilder("my-web-app")
    .description("My Python Web Application")
    .after("network-online.target")
    .wants("network-online.target")
    # [Service] section
    .type_("simple")
    .exec_start("/usr/bin/python3 /opt/my-web-app/main.py")
    .working_directory("/opt/my-web-app")
    .environment({"PORT": "8080", "LOG_LEVEL": "info"})
    .restart("on-failure")
    .restart_sec(5)
    # Security hardening
    .private_tmp(True)
    .protect_system("strict")
    .protect_home("yes")
    .dynamic_user(True)
    .state_directory("my-web-app")
    # [Install] section
    .wanted_by("default.target")
    .build()
)

# Preview the generated unit file
print("Generated unit file:")
print("-" * 50)
print(unit_file.content)
print("-" * 50)

# Install the unit file to ~/.config/systemd/user/ (user scope)
path = client.install(unit_file)
print(f"Installed to: {path}")

# Enable so it starts on login
result = client.enable("my-web-app.service")
for change in result.changes:
    print(f"  {change[0]} {change[1]} -> {change[2]}")

# Start the service now
client.start("my-web-app.service")

# Verify it is running
status = client.status("my-web-app.service")
print(f"\nState: {status.active_state} ({status.sub_state})")
if status.main_pid:
    print(f"PID:   {status.main_pid}")

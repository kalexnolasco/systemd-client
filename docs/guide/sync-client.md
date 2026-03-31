# Sync Client

The `SystemdClient` provides a synchronous interface wrapping the async internals. It's the simplest way to interact with systemd from Python.

## Creating a Client

```python
from systemd_client import SystemdClient, BackendType

# Auto-detect backend (tries D-Bus, falls back to subprocess)
client = SystemdClient()

# Force subprocess backend (recommended — zero dependencies)
client = SystemdClient(backend=BackendType.SUBPROCESS)

# Force D-Bus backend (requires dasbus)
client = SystemdClient(backend=BackendType.DBUS)
```

## Listing Units

```python
# All units
units = client.list_units()

# Filter by type
services = client.list_units(unit_type="service")
timers = client.list_units(unit_type="timer")

# Filter by state
active = client.list_units(state="active")
failed = client.list_units(state="failed")

# Combine filters
active_services = client.list_units(unit_type="service", state="active")
```

Each unit is a `UnitInfo` dataclass:

```python
for unit in services:
    print(f"{unit.name:<40} {unit.active_state:<10} {unit.sub_state}")
    # my-app.service                           active     running
```

## Unit Status

Get detailed information about a specific unit:

```python
from systemd_client import UnitNotFoundError

try:
    status = client.status("my-app.service")
except UnitNotFoundError:
    print("Unit not found!")
    raise

print(f"Name:        {status.name}")
print(f"Description: {status.description}")
print(f"Load:        {status.load_state}")
print(f"Active:      {status.active_state} ({status.sub_state})")
print(f"PID:         {status.main_pid}")
print(f"Unit file:   {status.fragment_path}")
print(f"Since:       {status.active_enter_timestamp}")
print(f"Result:      {status.result}")

# Access all raw properties
for key, value in status.properties.items():
    print(f"  {key}={value}")
```

## Unit Operations

```python
# Start / stop / restart / reload
client.start("my-app.service")
client.stop("my-app.service")
client.restart("my-app.service")
client.reload("my-app.service")

# Enable / disable
result = client.enable("my-app.service")
for change in result.changes:
    print(f"  {change[0]} {change[1]} -> {change[2]}")

result = client.disable("my-app.service")

# Mask / unmask (prevent starting entirely)
client.mask("my-app.service")
client.unmask("my-app.service")

# Reload daemon (after changing unit files)
client.daemon_reload()
```

All operations raise `UnitOperationError` on failure:

```python
from systemd_client import UnitOperationError

try:
    client.start("nonexistent.service")
except UnitOperationError as e:
    print(f"Failed to {e.operation} {e.unit_name}: {e.detail}")
```

## Boolean Checks

Quick state checks without fetching full status:

```python
client.is_active("my-app.service")   # -> bool
client.is_enabled("my-app.service")  # -> bool
client.is_failed("my-app.service")   # -> bool
```

## Journal Access

```python
from systemd_client import JournalPriority

# Recent entries
entries = client.journal("my-app.service", lines=50)

# With filters
entries = client.journal(
    "my-app.service",
    lines=100,
    since="1h ago",
    priority=JournalPriority.WARNING,
    grep="error|timeout",
)

for entry in entries:
    print(f"{entry.timestamp} [{entry.priority.name}] {entry.message}")

# Follow in real-time (blocking)
for entry in client.journal_follow("my-app.service"):
    print(entry.message)
```

## Complete Example: Deploy Workflow

```python
import time
from systemd_client import SystemdClient, UnitOperationError

def deploy(unit_name: str) -> bool:
    client = SystemdClient()

    # Reload daemon config (picks up unit file changes)
    client.daemon_reload()

    # Restart the service
    try:
        client.restart(unit_name)
    except UnitOperationError as e:
        print(f"Restart failed: {e}")
        return False

    # Wait and verify
    time.sleep(2)

    if client.is_failed(unit_name):
        status = client.status(unit_name)
        print(f"Service failed! Result: {status.result}")

        # Show recent errors
        for entry in client.journal(unit_name, lines=10):
            print(f"  {entry.message}")
        return False

    if client.is_active(unit_name):
        status = client.status(unit_name)
        print(f"Running with PID {status.main_pid}")
        return True

    print("Service not yet active...")
    return False

deploy("my-app.service")
```

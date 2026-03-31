# Sync Client

The `SystemdClient` is the simplest way to manage your **systemd user services** from Python. It wraps the async internals so you don't need to worry about `await` or event loops -- just call methods and get results.

Let's walk through everything you can do with it.

## Create a Client

First, import and instantiate the client:

```python hl_lines="3"
from systemd_client import SystemdClient, BackendType

client = SystemdClient()  # (1)!
```

1. By default, the client **auto-detects** the best backend. It tries D-Bus first, then falls back to subprocess.

??? tip "Other options for backend selection..."

    You can force a specific backend if you prefer:

    ```python hl_lines="2 5"
    # Subprocess only — zero extra dependencies, recommended
    client = SystemdClient(backend=BackendType.SUBPROCESS)

    # D-Bus only — requires dasbus
    client = SystemdClient(backend=BackendType.DBUS)
    ```

## List Units

Now you can list all your user units -- or filter them down to exactly what you need:

```python hl_lines="2 5 8"
# All units
units = client.list_units()

# Filter by type
services = client.list_units(unit_type="service")  # (1)!

# Filter by state
active = client.list_units(state="active")  # (2)!

# Combine filters
active_services = client.list_units(unit_type="service", state="active")
```

1. You can use `"service"`, `"timer"`, `"socket"`, `"target"`, and any other systemd unit type.
2. Common states: `"active"`, `"inactive"`, `"failed"`.

Each unit comes back as a `UnitInfo` frozen dataclass. Let's see what that looks like:

```python hl_lines="2"
for unit in services:
    print(f"{unit.name:<40} {unit.active_state:<10} {unit.sub_state}")
```

```console
$ python list_services.py
my-app.service                           active     running
my-worker.service                        active     running
my-scheduler.service                     inactive   dead
```

!!! check
    If you see your services listed, everything is working.

## Get Unit Status

Let's get detailed information about a specific unit:

```python hl_lines="4 8 9 10 11"
from systemd_client import UnitNotFoundError

try:
    status = client.status("my-app.service")  # (1)!
except UnitNotFoundError:
    print("Unit not found!")
    raise

print(f"Name:        {status.name}")
print(f"Description: {status.description}")
print(f"Load:        {status.load_state}")
print(f"Active:      {status.active_state} ({status.sub_state})")  # (2)!
print(f"PID:         {status.main_pid}")
print(f"Unit file:   {status.fragment_path}")
print(f"Since:       {status.active_enter_timestamp}")
print(f"Result:      {status.result}")
```

1. Returns a `UnitStatus` frozen dataclass with all the details you'd see from `systemctl --user status`.
2. `active_state` and `sub_state` are `StrEnum` values, so they work as both strings and enum members.

??? info "Technical Details"

    The `UnitStatus` object also has a `properties` dict with **every** raw property from systemd:

    ```python
    for key, value in status.properties.items():
        print(f"  {key}={value}")
    ```

    This is useful when you need access to properties not covered by the named fields.

## Unit Operations

Here's where it gets fun. You can start, stop, restart, and manage services just like you would from the terminal:

```python hl_lines="2 3 4 5 8 12 13 16"
# Start / stop / restart / reload
client.start("my-app.service")
client.stop("my-app.service")
client.restart("my-app.service")
client.reload("my-app.service")

# Enable / disable
result = client.enable("my-app.service")  # (1)!
for change in result.changes:
    print(f"  {change[0]} {change[1]} -> {change[2]}")

result = client.disable("my-app.service")

# Mask / unmask (prevent starting entirely)
client.mask("my-app.service")  # (2)!
client.unmask("my-app.service")

# Reload daemon (after changing unit files)
client.daemon_reload()  # (3)!
```

1. `enable()` returns an `EnableResult` with a list of symlink changes that were made.
2. Masking a unit **prevents it from being started** -- even manually. Useful for units you want to completely disable.
3. Always call `daemon_reload()` after editing `.service` files so systemd picks up the changes.

!!! warning
    All operations raise `UnitOperationError` on failure. Always handle this in production code:

    ```python
    from systemd_client import UnitOperationError

    try:
        client.start("nonexistent.service")
    except UnitOperationError as e:
        print(f"Failed to {e.operation} {e.unit_name}: {e.detail}")
    ```

## Quick Boolean Checks

Sometimes you just want a yes/no answer. These methods skip the full status fetch and return a simple `bool`:

```python hl_lines="1 2 3"
client.is_active("my-app.service")   # -> bool  # (1)!
client.is_enabled("my-app.service")  # -> bool
client.is_failed("my-app.service")   # -> bool
```

1. Under the hood, these use `systemctl is-active` (or the D-Bus equivalent), which is faster than fetching the full status.

!!! tip
    These are perfect for health checks and monitoring scripts where you don't need the full unit details.

## Read the Journal

You can read journal entries for any unit directly from the client:

```python hl_lines="4 7 8 9 10 11 12"
from systemd_client import JournalPriority

# Recent entries
entries = client.journal("my-app.service", lines=50)

# With filters
entries = client.journal(
    "my-app.service",
    lines=100,
    since="1h ago",
    priority=JournalPriority.WARNING,  # (1)!
    grep="error|timeout",  # (2)!
)

for entry in entries:
    print(f"{entry.timestamp} [{entry.priority.name}] {entry.message}")
```

1. This gives you entries at WARNING level **and above** (WARNING, ERR, CRIT, ALERT, EMERG).
2. The `grep` parameter accepts regex patterns, just like `journalctl --grep`.

You can also follow the journal in real-time:

```python hl_lines="1 2"
for entry in client.journal_follow("my-app.service"):  # (1)!
    print(entry.message)
```

1. This is a **blocking** iterator -- it runs forever until you press Ctrl+C. For non-blocking follow, use the [async client](async-client.md).

!!! info
    Journal reading **always** uses subprocess (`journalctl --user`) regardless of your backend choice. See [Backends](backends.md) for details.

## Putting It All Together: Deploy Workflow

Let's build a real-world deploy function that restarts a service and verifies it came up healthy:

```python hl_lines="7 10 16 17 20 25"
import time
from systemd_client import SystemdClient, UnitOperationError

def deploy(unit_name: str) -> bool:
    client = SystemdClient()

    client.daemon_reload()  # (1)!

    try:
        client.restart(unit_name)  # (2)!
    except UnitOperationError as e:
        print(f"Restart failed: {e}")
        return False

    time.sleep(2)  # (3)!

    if client.is_failed(unit_name):
        status = client.status(unit_name)
        print(f"Service failed! Result: {status.result}")

        for entry in client.journal(unit_name, lines=10):  # (4)!
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

1. Pick up any changes to the unit file before restarting.
2. Restart the service -- this will raise if systemd can't even attempt the restart.
3. Give the service a moment to start up (or crash).
4. If the service failed, grab the last 10 log lines to show what went wrong.

!!! check
    If the function prints `Running with PID ...`, your deploy was successful.

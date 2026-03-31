# Quick Start

## 5-Minute Overview

### List your services

```python
from systemd_client import SystemdClient

client = SystemdClient()

for unit in client.list_units(unit_type="service"):
    print(f"{unit.name}: {unit.active_state} ({unit.sub_state})")
```

### Check unit status

```python
status = client.status("my-app.service")
print(f"Name:   {status.name}")
print(f"State:  {status.active_state} ({status.sub_state})")
print(f"PID:    {status.main_pid}")
print(f"Since:  {status.active_enter_timestamp}")
```

### Manage units

```python
client.start("my-app.service")
client.restart("my-app.service")
client.stop("my-app.service")

# Enable/disable
result = client.enable("my-app.service")
print(result.changes)
```

### Query journal

```python
from systemd_client import JournalPriority

# Last 50 lines
entries = client.journal("my-app.service", lines=50)

# Errors from the last hour
errors = client.journal(
    "my-app.service",
    priority=JournalPriority.ERR,
    since="1h ago",
)

for entry in errors:
    print(f"[{entry.priority.name}] {entry.message}")
```

### Follow journal in real-time

```python
# Blocking iterator (Ctrl+C to stop)
for entry in client.journal_follow("my-app.service"):
    print(entry.message)
```

### Boolean checks

```python
if client.is_active("my-app.service"):
    print("Running!")

if client.is_failed("my-app.service"):
    print("Something went wrong")

if not client.is_enabled("my-app.service"):
    client.enable("my-app.service")
```

## Async Version

Every method above has an async equivalent:

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    # All methods are coroutines
    units = await client.list_units(unit_type="service")
    await client.restart("my-app.service")

    # Async generator for follow
    async for entry in client.journal_follow("my-app.service"):
        print(entry.message)

asyncio.run(main())
```

## CLI

```bash
# List units
systemd-client list
systemd-client list --type service

# Status
systemd-client status my-app.service

# Operations
systemd-client restart my-app.service

# Journal
systemd-client journal -u my-app.service -n 50
systemd-client journal -u my-app.service --follow

# JSON output
systemd-client --json list
```

## Next Steps

- [Sync Client Guide](../guide/sync-client.md) — Full sync API walkthrough
- [Async Client Guide](../guide/async-client.md) — Async patterns and concurrency
- [Journal Guide](../guide/journal.md) — Advanced journal queries
- [API Reference](../api/client.md) — Complete method signatures

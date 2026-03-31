# Examples

Ready-to-use scripts in the [`examples/`](https://github.com/kalexnolasco/systemd-client/tree/main/examples) directory. Copy, paste, run.

## Basic Operations

### List all services

```python title="examples/01_list_services.py"
from systemd_client import SystemdClient

client = SystemdClient()
services = client.list_units(unit_type="service")

for svc in services:
    print(f"{svc.name:<40} {svc.active_state:<12} {svc.sub_state}")
```

### Service status

```python title="examples/02_service_status.py"
from systemd_client import SystemdClient, UnitNotFoundError

client = SystemdClient()

try:
    status = client.status("my-app.service")
    print(f"State: {status.active_state} ({status.sub_state})")
    print(f"PID:   {status.main_pid}")
except UnitNotFoundError:
    print("Unit not found")
```

### Start / stop / restart

```python title="examples/03_start_stop_restart.py"
from systemd_client import SystemdClient

client = SystemdClient()
client.restart("my-app.service")
print(f"Active: {client.is_active('my-app.service')}")
```

### Enable / disable

```python title="examples/04_enable_disable.py"
from systemd_client import SystemdClient

client = SystemdClient()
result = client.enable("my-app.service")
for change in result.changes:
    print(f"  {change[0]} {change[1]} {change[2]}")
```

## Journal

### Query with filters

```python title="examples/05_journal_query.py"
from systemd_client import SystemdClient, JournalPriority

client = SystemdClient()

# Last 20 entries
entries = client.journal("my-app.service", lines=20)

# Warnings and above from the last hour
warnings = client.journal(
    "my-app.service",
    priority=JournalPriority.WARNING,
    since="1h ago",
)
```

### Follow in real-time

```python title="examples/06_journal_follow.py"
from systemd_client import SystemdClient

client = SystemdClient()
for entry in client.journal_follow("my-app.service"):
    print(f"{entry.timestamp} {entry.message}")
```

### Search by regex

```python title="examples/11_journal_grep.py"
from systemd_client import SystemdClient

client = SystemdClient()
entries = client.journal(grep="error|timeout", lines=50, since="24h ago")
for entry in entries:
    print(f"[{entry.priority.name}] {entry.message}")
```

## Async

### Concurrent operations

```python title="examples/07_async_client.py"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    # Both queries run in parallel
    units, journal = await asyncio.gather(
        client.list_units(unit_type="service"),
        client.journal(lines=10),
    )

    active = [u for u in units if u.active_state == "active"]
    print(f"{len(active)} active services")

asyncio.run(main())
```

### Async follow

```python title="examples/08_async_follow.py"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()
    async for entry in client.journal_follow("my-app.service"):
        print(entry.message)

asyncio.run(main())
```

## Operations

### Health check

```python title="examples/09_health_check.py"
import sys
from systemd_client import SystemdClient

client = SystemdClient()
units = ["app.service", "worker.service", "scheduler.service"]

all_ok = True
for unit in units:
    active = client.is_active(unit)
    failed = client.is_failed(unit)
    symbol = "FAIL" if failed else (" OK " if active else "DOWN")
    if not active:
        all_ok = False
    print(f"[{symbol}] {unit}")

sys.exit(0 if all_ok else 1)
```

### Failed units report

```python title="examples/10_failed_units_report.py"
from systemd_client import SystemdClient, JournalPriority

client = SystemdClient()
all_units = client.list_units()
failed = [u for u in all_units if u.active_state == "failed"]

for unit in failed:
    print(f"FAILED: {unit.name}")
    errors = client.journal(unit.name, priority=JournalPriority.ERR, lines=5)
    for e in errors:
        print(f"  {e.message}")
```

### Deploy workflow

```python title="examples/13_deploy_and_manage.py"
import time
from systemd_client import SystemdClient

client = SystemdClient()

client.daemon_reload()
client.restart("my-app.service")
time.sleep(2)

if client.is_failed("my-app.service"):
    for e in client.journal("my-app.service", lines=5):
        print(f"ERROR: {e.message}")
elif client.is_active("my-app.service"):
    status = client.status("my-app.service")
    print(f"Running with PID {status.main_pid}")
```

### Batch restart

```python title="examples/14_batch_operations.py"
from systemd_client import SystemdClient, UnitOperationError

client = SystemdClient()
units = ["app.service", "worker.service"]

for unit in units:
    try:
        client.restart(unit)
        print(f"[OK] {unit}")
    except UnitOperationError as e:
        print(f"[FAIL] {unit}: {e.detail}")
```

### Monitoring dashboard

```python title="examples/15_async_monitor_dashboard.py"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()
    units = ["app.service", "worker.service"]

    while True:
        results = await asyncio.gather(
            *(client.status(u) for u in units)
        )
        for s in results:
            print(f"{s.name}: {s.active_state} (PID {s.main_pid})")
        await asyncio.sleep(5)

asyncio.run(main())
```

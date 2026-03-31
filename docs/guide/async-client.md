# Async Client

The `AsyncSystemdClient` is the canonical implementation. All methods are coroutines. The sync `SystemdClient` is a thin wrapper around this.

## Creating a Client

```python
from systemd_client import AsyncSystemdClient, BackendType

client = AsyncSystemdClient()
client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
```

## Basic Usage

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    # List services
    units = await client.list_units(unit_type="service")
    for unit in units:
        print(f"{unit.name}: {unit.active_state}")

    # Status
    status = await client.status("my-app.service")
    print(f"PID: {status.main_pid}")

    # Operations
    await client.restart("my-app.service")
    is_active = await client.is_active("my-app.service")
    print(f"Active: {is_active}")

asyncio.run(main())
```

## Concurrent Operations

The real power of async — run multiple operations in parallel:

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    # Check multiple services simultaneously
    services = ["app.service", "worker.service", "scheduler.service"]

    results = await asyncio.gather(
        *(client.is_active(svc) for svc in services)
    )

    for svc, active in zip(services, results):
        print(f"{svc}: {'UP' if active else 'DOWN'}")

asyncio.run(main())
```

### Concurrent status + journal

```python
async def full_report(client, unit_name):
    status, journal = await asyncio.gather(
        client.status(unit_name),
        client.journal(unit_name, lines=10),
    )
    return status, journal
```

## Async Journal Follow

```python
async def follow_logs():
    client = AsyncSystemdClient()

    async for entry in client.journal_follow("my-app.service"):
        print(f"[{entry.priority.name}] {entry.message}")

# Run with Ctrl+C support
try:
    asyncio.run(follow_logs())
except KeyboardInterrupt:
    pass
```

### Follow with timeout

```python
async def follow_with_timeout(unit: str, seconds: int = 30):
    client = AsyncSystemdClient()

    async def _follow():
        async for entry in client.journal_follow(unit):
            print(entry.message)

    try:
        await asyncio.wait_for(_follow(), timeout=seconds)
    except asyncio.TimeoutError:
        print(f"Stopped after {seconds}s")
```

## Integration with Async Frameworks

### With FastAPI

```python
from fastapi import FastAPI
from systemd_client import AsyncSystemdClient

app = FastAPI()
client = AsyncSystemdClient()

@app.get("/services")
async def list_services():
    units = await client.list_units(unit_type="service")
    return [{"name": u.name, "state": u.active_state} for u in units]

@app.post("/services/{name}/restart")
async def restart_service(name: str):
    await client.restart(name)
    return {"status": "restarted"}
```

### With aiohttp

```python
from aiohttp import web
from systemd_client import AsyncSystemdClient

client = AsyncSystemdClient()

async def health_check(request):
    services = ["app.service", "db.service"]
    results = await asyncio.gather(
        *(client.is_active(s) for s in services)
    )
    all_ok = all(results)
    return web.json_response(
        {"healthy": all_ok},
        status=200 if all_ok else 503,
    )
```

## Error Handling

Same exceptions as the sync client — just use `try/await`:

```python
from systemd_client import UnitNotFoundError, UnitOperationError

try:
    await client.restart("my-app.service")
except UnitNotFoundError as e:
    print(f"Unit {e.unit_name} not found")
except UnitOperationError as e:
    print(f"Operation {e.operation} failed: {e.detail}")
```

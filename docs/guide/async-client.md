# Async Client

The `AsyncSystemdClient` is the **canonical implementation** -- all methods are native coroutines. The sync `SystemdClient` is actually a thin wrapper around this.

If you're building an async application (FastAPI, aiohttp, or just plain `asyncio`), this is the client for you.

## Create a Client

```python hl_lines="3"
from systemd_client import AsyncSystemdClient, BackendType

async with AsyncSystemdClient() as client:  # (1)!
    units = await client.list_units()
```

1. Use `async with` for proper resource cleanup. Same backend options as the sync client: `BackendType.AUTO` (default), `BackendType.SUBPROCESS`, or `BackendType.DBUS`. Add `scope=SystemdScope.SYSTEM` for system services.

## Basic Usage

Let's start with the fundamentals. Every method is a coroutine, so you'll `await` each call:

```python hl_lines="7 8 12 15 16"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    # List services
    units = await client.list_units(unit_type="service")  # (1)!
    for unit in units:
        print(f"{unit.name}: {unit.active_state}")

    status = await client.status("my-app.service")  # (2)!
    print(f"PID: {status.main_pid}")

    await client.restart("my-app.service")  # (3)!
    is_active = await client.is_active("my-app.service")
    print(f"Active: {is_active}")

asyncio.run(main())
```

1. Returns the same `list[UnitInfo]` as the sync client -- the data models are identical.
2. Returns a `UnitStatus` frozen dataclass.
3. All operations (`start`, `stop`, `restart`, `reload`, `enable`, `disable`, `mask`, `unmask`) work the same way.

!!! info
    The async client has the **exact same API** as the sync client -- just add `await` before each call. All the same exceptions, data models, and parameters apply.

## Concurrent Operations

Here's where the async client really shines. You can run **multiple operations in parallel** with `asyncio.gather`:

```python hl_lines="8 9 10"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()

    services = ["app.service", "worker.service", "scheduler.service"]
    results = await asyncio.gather(  # (1)!
        *(client.is_active(svc) for svc in services)
    )

    for svc, active in zip(services, results):
        print(f"{svc}: {'UP' if active else 'DOWN'}")

asyncio.run(main())
```

1. All three `is_active` calls run **simultaneously** instead of one after another. With three services, this is roughly 3x faster than sequential calls.

```console
$ python check_services.py
app.service: UP
worker.service: UP
scheduler.service: DOWN
```

!!! tip
    Use `asyncio.gather` any time you need to check or operate on multiple units. The speedup grows linearly with the number of services.

### Fetch Status and Journal at the Same Time

You can combine different operations in a single `gather` call too:

```python hl_lines="2 3 4"
async def full_report(client, unit_name):
    status, journal = await asyncio.gather(  # (1)!
        client.status(unit_name),
        client.journal(unit_name, lines=10),
    )
    return status, journal
```

1. The status fetch and journal read happen concurrently -- no waiting for one to finish before starting the other.

## Follow the Journal (Async)

The async journal follow is a **non-blocking** async generator. It yields entries as they arrive without blocking your event loop:

```python hl_lines="5 6"
async def follow_logs():
    client = AsyncSystemdClient()

    async for entry in client.journal_follow("my-app.service"):
        print(f"[{entry.priority.name}] {entry.message}")  # (1)!

try:
    asyncio.run(follow_logs())
except KeyboardInterrupt:
    pass  # (2)!
```

1. Each `JournalEntry` has `.timestamp`, `.priority`, `.message`, `.pid`, and many more fields.
2. Gracefully handle Ctrl+C -- the async generator cleans up automatically.

### Follow with a Timeout

Need to watch logs for a limited time? Wrap it with `asyncio.wait_for`:

```python hl_lines="8"
async def follow_with_timeout(unit: str, seconds: int = 30):
    client = AsyncSystemdClient()

    async def _follow():
        async for entry in client.journal_follow(unit):
            print(entry.message)

    try:
        await asyncio.wait_for(_follow(), timeout=seconds)  # (1)!
    except asyncio.TimeoutError:
        print(f"Stopped after {seconds}s")
```

1. After `seconds` elapses, `asyncio.wait_for` cancels the coroutine and raises `TimeoutError`.

## Integration with Async Frameworks

### FastAPI

The async client fits naturally into **FastAPI** endpoints:

```python hl_lines="5 8 9 13 14"
from fastapi import FastAPI
from systemd_client import AsyncSystemdClient

app = FastAPI()
client = AsyncSystemdClient()  # (1)!

@app.get("/services")
async def list_services():
    units = await client.list_units(unit_type="service")  # (2)!
    return [{"name": u.name, "state": u.active_state} for u in units]

@app.post("/services/{name}/restart")
async def restart_service(name: str):
    await client.restart(name)
    return {"status": "restarted"}
```

1. Create the client once at module level -- it's lightweight and reusable.
2. Since FastAPI is async-native, the `await` here doesn't block any other requests.

!!! check
    Your FastAPI app can now manage systemd services via HTTP endpoints.

### aiohttp

Works just as well with **aiohttp**:

```python hl_lines="7 8 9"
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
        status=200 if all_ok else 503,  # (1)!
    )
```

1. Returns **503 Service Unavailable** if any service is down -- useful for load balancer health checks.

## Error Handling

Same exceptions as the sync client -- just use `try` / `await`:

```python hl_lines="4 6 8"
from systemd_client import UnitNotFoundError, UnitOperationError

try:
    await client.restart("my-app.service")
except UnitNotFoundError as e:
    print(f"Unit {e.unit_name} not found")  # (1)!
except UnitOperationError as e:
    print(f"Operation {e.operation} failed: {e.detail}")  # (2)!
```

1. The unit doesn't exist at all.
2. The unit exists, but the operation failed (e.g., the service crashed on start).

!!! note
    For the full list of exceptions and their attributes, see [Error Handling](errors.md).

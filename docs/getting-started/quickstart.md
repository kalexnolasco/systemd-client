# Tutorial - First Steps

Let's build your first Python script that manages systemd services. We'll go
step by step, from listing services to following live logs.

!!! info "Prerequisites"
    Make sure you've completed the **[Installation](installation.md)** guide and
    that `systemd-client` is working on your system.

## 1. Create a client

Create a file called `main.py` and add:

```python title="main.py" hl_lines="1 3"
from systemd_client import SystemdClient  # (1)!

client = SystemdClient()  # (2)!
```

1. Import the synchronous client. That's the only import you need to get started.
2. Create a client instance. By default it uses the subprocess backend, which
   calls `systemctl --user` and `journalctl --user` under the hood -- no extra
   dependencies required.

!!! tip
    The `SystemdClient` is lightweight and cheap to create. You can create it
    once and reuse it, or create a new one each time -- there's no connection
    to manage.

## 2. List your services

Now let's list all running user services. Add this to your script:

```python title="main.py" hl_lines="5-6"
from systemd_client import SystemdClient

client = SystemdClient()

for unit in client.list_units(unit_type="service"):  # (1)!
    print(f"{unit.name}: {unit.active_state} ({unit.sub_state})")  # (2)!
```

1. `list_units()` returns a list of `UnitInfo` objects. The `unit_type` filter
   narrows it to services only (you could also use `"timer"`, `"socket"`, etc.).
2. Each `UnitInfo` has typed attributes like `name`, `active_state`, `sub_state`,
   `load_state`, and `description` -- no string parsing needed.

Run it:

```console
$ python main.py
```

!!! check "You should see"
    ```
    dbus.service: active (running)
    my-app.service: active (running)
    pipewire.service: active (running)
    ...
    ```
    The exact output depends on what user services you have running.

??? info "Filtering by state"
    You can also filter by state to find, say, only failed services:

    ```python
    failed = client.list_units(unit_type="service", state="failed")
    for unit in failed:
        print(f"FAILED: {unit.name}")
    ```

## 3. Check unit status

Let's get detailed information about a specific service. Replace the content of
`main.py` with:

```python title="main.py" hl_lines="5-10"
from systemd_client import SystemdClient

client = SystemdClient()

status = client.status("dbus.service")  # (1)!

print(f"Name:   {status.name}")
print(f"State:  {status.active_state} ({status.sub_state})")  # (2)!
print(f"PID:    {status.main_pid}")
print(f"Since:  {status.active_enter_timestamp}")  # (3)!
```

1. `status()` returns a `UnitStatus` object with detailed properties. Pass the
   full unit name including the suffix.
2. `active_state` is the high-level state (`"active"`, `"inactive"`, `"failed"`).
   `sub_state` gives more detail (`"running"`, `"dead"`, `"exited"`).
3. `active_enter_timestamp` is a `datetime` object -- you can format it, compare
   it, or do math with it.

```console
$ python main.py
```

!!! check "You should see"
    ```
    Name:   dbus.service
    State:  active (running)
    PID:    1234
    Since:  2026-03-31 08:15:22
    ```

!!! note
    If you get a `UnitNotFoundError`, the unit doesn't exist. Always use the full
    unit name with its suffix (e.g., `my-app.service`, not just `my-app`).

## 4. Start and stop a service

Now let's manage a service. The client has `start()`, `stop()`, `restart()`, and
`reload()` methods:

```python title="main.py" hl_lines="5-7 9-10"
from systemd_client import SystemdClient

client = SystemdClient()

client.stop("my-app.service")   # (1)!
print(f"Active: {client.is_active('my-app.service')}")  # (2)!

client.start("my-app.service")  # (3)!
print(f"Active: {client.is_active('my-app.service')}")

status = client.status("my-app.service")
print(f"PID:    {status.main_pid}")
```

1. `stop()` sends the stop command and waits for systemd to acknowledge it.
2. `is_active()` is a quick boolean check -- much cheaper than calling `status()`
   when you only need to know if it's running.
3. `start()` brings the service back up.

```console
$ python main.py
```

!!! check "You should see"
    ```
    Active: False
    Active: True
    PID:    5678
    ```

!!! warning
    Replace `my-app.service` with an actual user service you have. If you don't
    have one, `dbus.service` is always available -- but be careful stopping
    system-critical services.

??? info "Enable and disable"
    To control whether a service starts at boot, use `enable()` and `disable()`:

    ```python
    result = client.enable("my-app.service")  # (1)!
    for change in result.changes:
        print(f"  {change[0]} {change[1]} -> {change[2]}")

    client.disable("my-app.service")
    ```

    1. `enable()` returns an `EnableResult` with a list of symlink changes that
       were made.

## 5. Query the journal

One of the most powerful features: reading service logs with structured data.
Let's query the last 20 log entries for a service:

```python title="main.py" hl_lines="1 5-6 8-9"
from systemd_client import SystemdClient, JournalPriority  # (1)!

client = SystemdClient()

entries = client.journal("my-app.service", lines=20)  # (2)!
for entry in entries:
    print(f"[{entry.priority.name}] {entry.message}")  # (3)!

errors = client.journal(  # (4)!
    "my-app.service",
    priority=JournalPriority.ERR,
    since="1h ago",
)
print(f"\nErrors in last hour: {len(errors)}")
```

1. Import `JournalPriority` to filter by log level.
2. `journal()` returns a list of `JournalEntry` objects. Each one has typed
   fields: `message`, `priority`, `timestamp`, `pid`, and more.
3. `priority` is a `JournalPriority` enum with levels from `EMERG` (0) to
   `DEBUG` (7).
4. Combine filters: get only errors (`priority <= ERR`) from the last hour.
   The `since` parameter accepts human-friendly strings like `"1h ago"`,
   `"today"`, or ISO dates like `"2026-03-31"`.

```console
$ python main.py
```

!!! check "You should see"
    ```
    [INFO] Starting application...
    [INFO] Listening on port 8080
    [WARNING] Slow query detected (1.2s)
    [INFO] Request handled in 45ms
    ...

    Errors in last hour: 0
    ```

??? tip "More journal filters"
    The `journal()` method supports several filters you can combine:

    ```python
    entries = client.journal(
        "my-app.service",
        lines=100,           # last N entries
        since="2h ago",      # start time
        until="30m ago",     # end time
        priority=JournalPriority.WARNING,  # WARNING and above
        grep="timeout|error",  # regex filter on message text
    )
    ```

    See the **[Journal Guide](../guide/journal.md)** for the full set of options.

## 6. Follow the journal in real-time

You can tail the journal live, like `journalctl -f`. This creates a blocking
iterator that yields new entries as they arrive:

```python title="main.py" hl_lines="5-7"
from systemd_client import SystemdClient

client = SystemdClient()

for entry in client.journal_follow("my-app.service"):  # (1)!
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"{ts} [{entry.priority.name}] {entry.message}")
```

1. `journal_follow()` returns an iterator that blocks until a new log line
   arrives. Press ++ctrl+c++ to stop.

```console
$ python main.py
```

!!! check "You should see"
    New log lines appearing in real-time as the service produces output:
    ```
    14:23:01 [INFO] Request handled in 12ms
    14:23:05 [INFO] Request handled in 8ms
    14:23:12 [WARNING] Connection pool near limit
    ...
    ```
    Press ++ctrl+c++ to stop following.

## 7. The async version

Everything you've seen above also works with `async`/`await`. The
`AsyncSystemdClient` has the exact same API -- every method is a coroutine:

```python title="main_async.py" hl_lines="1-2 4-5 7-8 11-12 15-16"
import asyncio
from systemd_client import AsyncSystemdClient  # (1)!

async def main():
    client = AsyncSystemdClient()  # (2)!

    # List services -- same API, just await it
    units = await client.list_units(unit_type="service")  # (3)!
    for unit in units:
        print(f"{unit.name}: {unit.active_state}")

    # Operations are coroutines too
    await client.restart("my-app.service")  # (4)!

    # Async generator for follow
    async for entry in client.journal_follow("my-app.service"):  # (5)!
        print(entry.message)

asyncio.run(main())
```

1. Import `AsyncSystemdClient` instead of `SystemdClient`.
2. Create the async client the same way -- no connection setup needed.
3. Every method that was synchronous is now a coroutine. Just add `await`.
4. Unit operations (`start`, `stop`, `restart`, etc.) are all coroutines.
5. `journal_follow()` becomes an async generator -- use `async for` instead
   of `for`.

!!! tip "When to use async?"
    Use `AsyncSystemdClient` when you're already in an async context (FastAPI,
    aiohttp, or any `asyncio` application), or when you need to monitor
    multiple services concurrently with `asyncio.gather()`. For simple scripts,
    the sync `SystemdClient` is perfectly fine.

??? info "Concurrent operations with async"
    The real power of async is running operations in parallel:

    ```python
    import asyncio
    from systemd_client import AsyncSystemdClient

    async def main():
        client = AsyncSystemdClient()
        services = ["app.service", "worker.service", "scheduler.service"]

        # Check all three simultaneously
        results = await asyncio.gather(
            *(client.is_active(svc) for svc in services)
        )

        for svc, active in zip(services, results):
            print(f"{svc}: {'UP' if active else 'DOWN'}")

    asyncio.run(main())
    ```

## 8. Quick CLI demo

`systemd-client` also ships with a command-line tool. You don't need to write
Python at all for common tasks:

```console
$ systemd-client list --type service
```

```console
$ systemd-client status my-app.service
```

```console
$ systemd-client restart my-app.service
```

```console
$ systemd-client journal -u my-app.service -n 50
```

```console
$ systemd-client journal -u my-app.service --follow
```

And if you want machine-readable output, add `--json`:

```console
$ systemd-client --json list | jq '.[] | select(.active_state == "failed")'
```

!!! tip
    The CLI is great for quick checks and scripting. See the full
    **[CLI Guide](../guide/cli.md)** for all commands and options.

## Next steps

You've covered the basics. Here's where to go from here:

- **[Sync Client Guide](../guide/sync-client.md)** -- Full walkthrough of the
  synchronous API, including error handling and the deploy workflow pattern.
- **[Async Client Guide](../guide/async-client.md)** -- Async patterns,
  concurrent operations, and integration with FastAPI and aiohttp.
- **[Journal Guide](../guide/journal.md)** -- Advanced journal queries, the
  low-level `JournalReader`, priority levels, and extra fields.
- **[Backends Guide](../guide/backends.md)** -- Subprocess vs. D-Bus backends,
  auto-detection, and when to use each.
- **[CLI Guide](../guide/cli.md)** -- All CLI commands, flags, JSON output, and
  exit codes.
- **[API Reference](../api/client.md)** -- Complete method signatures and
  type annotations.

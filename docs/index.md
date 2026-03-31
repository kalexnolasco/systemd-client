<div align="center" markdown>

# systemd-client

[![PyPI](https://img.shields.io/pypi/v/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Python](https://img.shields.io/pypi/pyversions/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![License](https://img.shields.io/pypi/l/systemd-client?style=flat-square)](https://github.com/kalexnolasco/systemd-client/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/kalexnolasco/systemd-client/tests.yml?style=flat-square&label=tests)](https://github.com/kalexnolasco/systemd-client/actions)

*A modern, Pythonic client for managing systemd user services.*

</div>

---

**systemd-client** is a high-level Python library for managing **systemd user services**. It gives you a clean, typed API instead of shelling out to `systemctl` and parsing text output by hand.

It is designed to be **easy to use**, **async-first** (with sync wrappers that feel just as natural), and **fully typed** so your editor and type checker can help you every step of the way.

The key ideas are:

- **Pythonic**: Frozen dataclasses, StrEnums, and full type annotations -- no string parsing.
- **Async-first**: Built on `asyncio` from the ground up. Use `AsyncSystemdClient` directly, or use the synchronous `SystemdClient` wrapper -- same API, same types.
- **Zero required dependencies**: The default subprocess backend calls `systemctl --user` under the hood and needs nothing beyond the standard library.
- **Pluggable**: Swap in the D-Bus backend for direct communication when you need it.

---

## Features

- **Async + Sync API** - `AsyncSystemdClient` for `async`/`await` code, `SystemdClient` as a synchronous wrapper. Both share the same interface and return the same typed models.
- **Pluggable Backends** - The default subprocess backend has zero dependencies. Install `systemd-client[dbus]` for a D-Bus backend via `dasbus` when you need direct communication.
- **Journal Reader** - Query and follow journal entries as structured `JournalEntry` objects. Filter by unit, priority, time range, or grep pattern.
- **Full Unit Management** - Start, stop, restart, reload, enable, disable, mask, unmask, status, `daemon-reload` -- everything `systemctl --user` can do.
- **Typed Models** - Frozen dataclasses with slots for `UnitInfo`, `UnitStatus`, `JournalEntry`, and `EnableResult`. StrEnums for every state and priority level.
- **Modern Python** - Requires Python 3.11+. Uses `StrEnum`, `slots=True` dataclasses, full PEP 561 type annotations.
- **CLI Included** - The `systemd-client` command gives you colored table output and a `--json` mode for scripting.

---

## Installation

```console
$ pip install systemd-client
---> 100%
Successfully installed systemd-client
```

You can also install it with optional extras:

```console
$ pip install systemd-client[dbus]
```

```console
$ pip install systemd-client[all]
```

!!! tip
    You only need the base install for most use cases. The subprocess backend works
    everywhere `systemctl --user` is available -- no extra packages required.

---

## Example

### Create it

Create a file `main.py` with:

```python hl_lines="1 3 6 10"
from systemd_client import SystemdClient  # (1)!

client = SystemdClient()  # (2)!

# List all running services in one call
for unit in client.list_units(unit_type="service"):  # (3)!
    print(f"{unit.name}: {unit.active_state}")

# Get detailed, typed status for a single unit
status = client.status("my-app.service")  # (4)!
print(f"PID {status.main_pid} running since {status.active_enter_timestamp}")
```

1. Import `SystemdClient` -- the synchronous client. For async code, use `AsyncSystemdClient` instead.
2. Create a client instance. The default backend is `auto`, which picks subprocess (or D-Bus if available).
3. `list_units()` returns a list of `UnitInfo` dataclasses. Filter by `unit_type` or `state`.
4. `status()` returns a `UnitStatus` dataclass with typed fields like `main_pid`, `active_state`, and timestamps.

### Check it

Run it:

```console
$ python main.py
my-app.service: active
my-worker.service: active
PID 12345 running since 2026-03-31 08:00:00
```

!!! check
    You get back **real Python objects** -- frozen dataclasses with typed fields -- not
    raw strings from `systemctl` output.

---

### Async example

If you are building an async application, use `AsyncSystemdClient` directly:

```python hl_lines="1 5 8"
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()  # (1)!

    # Start a service and verify it is running
    await client.start("my-app.service")  # (2)!
    is_running = await client.is_active("my-app.service")
    print(f"Running: {is_running}")

asyncio.run(main())
```

1. Same API shape as `SystemdClient`, but every method is a coroutine.
2. `start()`, `stop()`, `restart()`, `reload()` -- all the operations you expect, as awaitable calls.

### Check it

```console
$ python main.py
Running: True
```

---

### Read the journal

Query journal entries as structured Python objects:

```python hl_lines="4 5"
from systemd_client import SystemdClient

client = SystemdClient()
entries = client.journal(unit="my-app.service", lines=5)  # (1)!
for entry in entries:
    print(f"[{entry.priority}] {entry.timestamp}: {entry.message}")  # (2)!
```

1. Returns a list of `JournalEntry` dataclasses. You can also filter by `since`, `until`, `priority`, and `grep`.
2. Each entry has typed fields: `message`, `priority`, `timestamp`, `pid`, `unit`, and more.

### Check it

```console
$ python main.py
[6] 2026-03-31 08:01:22: Server started on port 8080
[6] 2026-03-31 08:01:23: Accepting connections
[6] 2026-03-31 08:05:00: Healthcheck OK
[4] 2026-03-31 08:10:15: Connection pool nearing limit
[6] 2026-03-31 08:10:16: Scaled pool to 200 connections
```

!!! info
    You can also **follow** the journal in real time with `client.journal_follow()`,
    which yields entries as they arrive -- as a synchronous iterator or an async generator.

---

## Requirements

**systemd-client** requires **Python 3.11+** and a Linux system with a running systemd user session.

The base install has **zero Python dependencies** -- it calls `systemctl --user` and `journalctl --user` via subprocess.

Optional dependencies:

- `dasbus` -- for the D-Bus backend (`pip install systemd-client[dbus]`)
- `pydantic` -- for Pydantic model variants (`pip install systemd-client[pydantic]`)

!!! note
    The subprocess backend is the default and works on any system where `systemctl --user`
    is available. You do not need D-Bus unless you have a specific reason to use it.

---

## Architecture

```mermaid
graph TD
    subgraph APP["Your Application"]
        SYNC["SystemdClient<br/><small>Synchronous API</small>"]
        ASYNC["AsyncSystemdClient<br/><small>Async API</small>"]
    end

    subgraph BACKENDS["Backends"]
        SUB["SubprocessBackend<br/><small>systemctl --user</small>"]
        DBUS["DBusBackend<br/><small>dasbus · optional</small>"]
    end

    subgraph JOURNAL["Journal"]
        JR["AsyncJournalReader<br/><small>journalctl --user --output=json</small>"]
    end

    subgraph SYSTEMD["systemd user session"]
        UNITS[("User Units<br/><small>services, timers, sockets</small>")]
        JRNL[("Journal<br/><small>log entries</small>")]
    end

    SYNC --> ASYNC
    ASYNC --> SUB
    ASYNC --> DBUS
    ASYNC --> JR
    SUB --> UNITS
    DBUS --> UNITS
    JR --> JRNL

    style APP fill:#d0ebff,stroke:#1971c2,stroke-width:2px
    style BACKENDS fill:#b2f2bb,stroke:#2f9e44,stroke-width:2px
    style JOURNAL fill:#f3d9fa,stroke:#9c36b5,stroke-width:2px
    style SYSTEMD fill:#fff3bf,stroke:#f08c00,stroke-width:2px
```

`SystemdClient` is a thin synchronous wrapper around `AsyncSystemdClient`. Under the hood, every call goes through a pluggable backend (subprocess or D-Bus) to talk to your systemd user session. Journal reads go through a dedicated `AsyncJournalReader` that parses JSON output from `journalctl`.

---

## License

This project is licensed under the terms of the **MIT license**.

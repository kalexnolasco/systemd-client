# systemd-client

[![PyPI](https://img.shields.io/pypi/v/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Python](https://img.shields.io/pypi/pyversions/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![License](https://img.shields.io/pypi/l/systemd-client?style=flat-square)](https://github.com/kalexnolasco/systemd-client/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/kalexnolasco/systemd-client/tests.yml?style=flat-square&label=tests)](https://github.com/kalexnolasco/systemd-client/actions)
[![Docs](https://img.shields.io/badge/docs-kalexnolasco.github.io-blue?style=flat-square)](https://kalexnolasco.github.io/systemd-client/)

High-level Python client for systemd services (user + system scope). Async-first with sync wrappers, subprocess + optional D-Bus backends, CLI included.

> **Documentation: [kalexnolasco.github.io/systemd-client](https://kalexnolasco.github.io/systemd-client/)**

## Features

- **Async + Sync API** — `AsyncSystemdClient` and `SystemdClient` with identical interfaces
- **User + System scope** — manage user session or system-wide services
- **Unit management** — list, status, cat, start, stop, restart, reload, try-restart, reload-or-restart, enable, disable, mask, unmask, reset-failed, batch ops
- **Journal reader** — query with filters (unit, priority, time range, grep) and real-time follow
- **Pluggable backends** — subprocess (default, zero deps) or D-Bus via dasbus
- **Context managers** — `with SystemdClient()` / `async with AsyncSystemdClient()` for cleanup
- **Typed models** — frozen dataclasses with full annotations, optional Pydantic support
- **CLI** — `systemd-client` command with table/JSON output, scope, batch, and no-block support
- **Modern Python** — 3.11+, StrEnum, slots, PEP 561 typed

## Install

```bash
pip install systemd-client
```

Optional extras:

```bash
pip install systemd-client[dbus]      # D-Bus backend via dasbus
pip install systemd-client[pydantic]  # Pydantic model variants
pip install systemd-client[all]       # Everything
```

## Quick Start

### Sync

```python
from systemd_client import SystemdClient

with SystemdClient() as client:
    # List services
    for unit in client.list_units(unit_type="service"):
        print(f"{unit.name}: {unit.active_state} ({unit.sub_state})")

    # Manage units
    client.restart("my-app.service")
    status = client.status("my-app.service")
    print(f"PID: {status.main_pid}, State: {status.active_state}")

    # Batch operations
    client.restart_units(["app.service", "worker.service"])

    # Journal
    entries = client.journal("my-app.service", lines=50, since="1h ago")
    for entry in entries:
        print(f"[{entry.priority}] {entry.message}")
```

### Async

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    async with AsyncSystemdClient() as client:
        units = await client.list_units(unit_type="service")
        await client.restart("my-app.service")

        async for entry in client.journal_follow("my-app.service"):
            print(entry.message)

asyncio.run(main())
```

### System Scope

```python
from systemd_client import SystemdClient, SystemdScope

with SystemdClient(scope=SystemdScope.SYSTEM) as client:
    units = client.list_units(unit_type="service")
```

## CLI

```bash
systemd-client list                                     # List all units
systemd-client list --type service                      # List services only
systemd-client list-unit-files --state enabled          # List installed unit files
systemd-client status my-app.service                    # Unit status
systemd-client cat my-app.service                       # Show unit file content
systemd-client restart my-app.service                   # Restart
systemd-client start a.service b.service                # Batch start
systemd-client restart --no-block my-app.service        # Non-blocking restart
systemd-client try-restart my-app.service               # Restart only if active
systemd-client reset-failed my-app.service              # Reset failed state
systemd-client journal -u my-app.service -n 50          # Last 50 log lines
systemd-client journal -u my-app.service --follow       # Follow logs
systemd-client --scope system list                      # System scope
systemd-client --json list                              # JSON output
```

## Architecture

```
Your Application
    |
    +-- SystemdClient (sync)
    |       |
    +-- AsyncSystemdClient (async)
            |
            +-- SubprocessBackend ---- systemctl --user/--system ----> systemd
            |     (default)
            +-- DBusBackend ---------- D-Bus session/system bus ----> systemd
            |     (optional, dasbus)
            +-- AsyncJournalReader --- journalctl --output=json -----> journal
```

## API Reference

| Method | Return | Description |
|--------|--------|-------------|
| `list_units(unit_type?, state?)` | `list[UnitInfo]` | List loaded units |
| `list_unit_files(unit_type?, state?)` | `list[UnitFileInfo]` | List installed unit files |
| `status(unit)` | `UnitStatus` | Detailed status |
| `cat(unit)` | `str` | Unit file content |
| `start(unit, no_block?)` | `None` | Start unit |
| `stop(unit, no_block?)` | `None` | Stop unit |
| `restart(unit, no_block?)` | `None` | Restart unit |
| `reload(unit, no_block?)` | `None` | Reload unit |
| `try_restart(unit, no_block?)` | `None` | Restart if active |
| `reload_or_restart(unit, no_block?)` | `None` | Reload or restart |
| `start_units(units, no_block?)` | `None` | Batch start |
| `stop_units(units, no_block?)` | `None` | Batch stop |
| `restart_units(units, no_block?)` | `None` | Batch restart |
| `enable(unit)` | `EnableResult` | Enable unit |
| `disable(unit)` | `EnableResult` | Disable unit |
| `mask(unit)` / `unmask(unit)` | `EnableResult` | Mask/unmask |
| `is_active(unit)` | `bool` | Check active |
| `is_enabled(unit)` | `bool` | Check enabled |
| `is_failed(unit)` | `bool` | Check failed |
| `daemon_reload()` | `None` | Reload daemon |
| `reset_failed(unit?)` | `None` | Reset failed state |
| `journal(unit?, lines?, ...)` | `list[JournalEntry]` | Query journal |
| `journal_follow(unit?, lines?, ...)` | `Iterator[JournalEntry]` | Follow journal |

## Examples

See the [`examples/`](https://github.com/kalexnolasco/systemd-client/tree/main/examples) directory for 15 ready-to-use scripts covering:

- Listing and monitoring services
- Start/stop/restart/enable operations
- Journal queries and real-time follow
- Health checks and failed unit reports
- Async concurrent operations
- Deploy workflows
- Batch operations

## Requirements

- Python >= 3.11
- Linux with systemd
- `systemctl` and `journalctl` on PATH

## License

[LGPL-2.1-or-later](LICENSE)

---

**systemd-client** · [Documentation](https://kalexnolasco.github.io/systemd-client/) · [GitHub](https://github.com/kalexnolasco/systemd-client) · [PyPI](https://pypi.org/project/systemd-client/)

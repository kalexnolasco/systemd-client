# systemd-client

[![PyPI](https://img.shields.io/pypi/v/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Python](https://img.shields.io/pypi/pyversions/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![License](https://img.shields.io/pypi/l/systemd-client?style=flat-square)](https://github.com/kalexnolasco/systemd-client/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/kalexnolasco/systemd-client/tests.yml?style=flat-square&label=tests)](https://github.com/kalexnolasco/systemd-client/actions)
[![Docs](https://img.shields.io/badge/docs-kalexnolasco.github.io-blue?style=flat-square)](https://kalexnolasco.github.io/systemd-client/)

High-level Python client for systemd user services. Async-first with sync wrappers, subprocess + optional D-Bus backends, CLI included.

> **Documentation: [kalexnolasco.github.io/systemd-client](https://kalexnolasco.github.io/systemd-client/)**

## Features

- **Async + Sync API** — `AsyncSystemdClient` and `SystemdClient` with identical interfaces
- **Unit management** — list, status, start, stop, restart, reload, enable, disable, mask, unmask
- **Journal reader** — query with filters (unit, priority, time range, grep) and real-time follow
- **Pluggable backends** — subprocess (default, zero deps) or D-Bus via dasbus
- **Typed models** — frozen dataclasses with full annotations, optional Pydantic support
- **CLI** — `systemd-client` command with table and JSON output
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

client = SystemdClient()

# List services
for unit in client.list_units(unit_type="service"):
    print(f"{unit.name}: {unit.active_state} ({unit.sub_state})")

# Manage units
client.restart("my-app.service")
status = client.status("my-app.service")
print(f"PID: {status.main_pid}, State: {status.active_state}")

# Journal
entries = client.journal("my-app.service", lines=50, since="1h ago")
for entry in entries:
    print(f"[{entry.priority}] {entry.message}")

# Follow journal in real-time
for entry in client.journal_follow("my-app.service"):
    print(entry.message)
```

### Async

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    client = AsyncSystemdClient()
    units = await client.list_units(unit_type="service")
    await client.restart("my-app.service")

    async for entry in client.journal_follow("my-app.service"):
        print(entry.message)

asyncio.run(main())
```

## CLI

```bash
systemd-client list                                     # List all units
systemd-client list --type service                      # List services only
systemd-client status my-app.service                    # Unit status
systemd-client restart my-app.service                   # Restart
systemd-client journal -u my-app.service -n 50          # Last 50 log lines
systemd-client journal -u my-app.service --follow       # Follow logs
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
            +-- SubprocessBackend ---- systemctl --user ----> systemd
            |     (default)
            +-- DBusBackend ---------- D-Bus session bus ---> systemd
            |     (optional, dasbus)
            +-- AsyncJournalReader --- journalctl --user ---> journal
```

## API Reference

| Method | Return | Description |
|--------|--------|-------------|
| `list_units(unit_type?, state?)` | `list[UnitInfo]` | List user units |
| `status(unit)` | `UnitStatus` | Detailed status |
| `start(unit)` | `None` | Start unit |
| `stop(unit)` | `None` | Stop unit |
| `restart(unit)` | `None` | Restart unit |
| `reload(unit)` | `None` | Reload unit |
| `enable(unit)` | `EnableResult` | Enable unit |
| `disable(unit)` | `EnableResult` | Disable unit |
| `mask(unit)` / `unmask(unit)` | `EnableResult` | Mask/unmask |
| `is_active(unit)` | `bool` | Check active |
| `is_enabled(unit)` | `bool` | Check enabled |
| `is_failed(unit)` | `bool` | Check failed |
| `daemon_reload()` | `None` | Reload daemon |
| `journal(unit?, lines?, since?, until?, priority?, grep?)` | `list[JournalEntry]` | Query journal |
| `journal_follow(unit?, lines?, priority?)` | `Iterator[JournalEntry]` | Follow journal |

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

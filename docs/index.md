# systemd-client

<div align="center" markdown>

[![PyPI](https://img.shields.io/pypi/v/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Python](https://img.shields.io/pypi/pyversions/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![License](https://img.shields.io/pypi/l/systemd-client?style=flat-square)](https://github.com/kalexnolasco/systemd-client/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/kalexnolasco/systemd-client/tests.yml?style=flat-square&label=tests)](https://github.com/kalexnolasco/systemd-client/actions)

**High-level Python client for systemd user services**

*Async-first with sync wrappers, subprocess + optional D-Bus backends, CLI included.*

</div>

---

## Why systemd-client?

Managing systemd user services from Python typically means shelling out to `systemctl` and parsing text output. **systemd-client** gives you a clean, typed API that works the way you'd expect:

```python
from systemd_client import SystemdClient

client = SystemdClient()

# One line to check all your services
for unit in client.list_units(unit_type="service"):
    print(f"{unit.name}: {unit.active_state}")

# Typed results, not string parsing
status = client.status("my-app.service")
print(f"PID {status.main_pid} running since {status.active_enter_timestamp}")
```

## Key Features

| | Feature | Description |
|:-:|---------|-------------|
| **:material-sync:** | **Async + Sync** | Async-first design with synchronous wrappers. Use `AsyncSystemdClient` or `SystemdClient` — same API, same types. |
| **:material-cog:** | **Pluggable Backends** | Subprocess backend (zero deps, default) or D-Bus via dasbus for direct communication. |
| **:material-text-box-search:** | **Journal Reader** | Query and follow journal entries with structured `JournalEntry` objects. Filter by unit, priority, time range, grep. |
| **:material-wrench:** | **Full Unit Management** | Start, stop, restart, reload, enable, disable, mask, unmask, status — everything `systemctl --user` does. |
| **:material-language-python:** | **Modern Python** | Python 3.11+ with StrEnum, frozen dataclasses, full type annotations, PEP 561 typed. |
| **:material-console:** | **CLI Included** | `systemd-client` command with colored table output and JSON mode. |

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

## Quick Install

```bash
pip install systemd-client
```

Optional extras:

=== "D-Bus backend"

    ```bash
    pip install systemd-client[dbus]
    ```

=== "Pydantic models"

    ```bash
    pip install systemd-client[pydantic]
    ```

=== "Everything"

    ```bash
    pip install systemd-client[all]
    ```

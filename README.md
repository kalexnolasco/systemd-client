# systemd-client

[![PyPI](https://img.shields.io/pypi/v/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Python](https://img.shields.io/pypi/pyversions/systemd-client?style=flat-square)](https://pypi.org/project/systemd-client/)
[![License](https://img.shields.io/pypi/l/systemd-client?style=flat-square)](https://github.com/kalexnolasco/systemd-client/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/kalexnolasco/systemd-client/tests.yml?style=flat-square&label=tests)](https://github.com/kalexnolasco/systemd-client/actions)
[![286 tests](https://img.shields.io/badge/tests-286%20passed-brightgreen?style=flat-square)](https://github.com/kalexnolasco/systemd-client/actions)
[![Beta](https://img.shields.io/badge/status-beta-blue?style=flat-square)](https://pypi.org/project/systemd-client/)
[![Docs](https://img.shields.io/badge/docs-kalexnolasco.github.io-blue?style=flat-square)](https://kalexnolasco.github.io/systemd-client/)

**The definitive Python library for systemd.** Manage services, create units, read journals, analyze security, control resources, and monitor everything — from Python or the terminal.

> **Documentation: [kalexnolasco.github.io/systemd-client](https://kalexnolasco.github.io/systemd-client/)**

## Features

| Category | What you can do |
|----------|----------------|
| **Unit Management** | list, status, cat, start, stop, restart, reload, try-restart, reload-or-restart, enable, disable, mask, unmask, reset-failed, kill |
| **Unit File Builder** | Create .service, .timer, .socket, .path files with a fluent Python API |
| **Install / Uninstall** | Deploy unit files, create drop-in overrides, uninstall units |
| **Transient Units** | Run commands as systemd services without creating files (systemd-run) |
| **Journal** | Query with filters (unit, priority, time range, grep) + real-time follow |
| **Resource Control** | Set cgroup limits (CPU, memory, IO), monitor usage, list timers/sockets/dependencies |
| **Security Analysis** | Boot blame, security scoring (0-10 exposure), unit file verification |
| **sd_notify** | Notify systemd from your Python service (READY, STATUS, WATCHDOG) |
| **Power Management** | poweroff, reboot, suspend, hibernate |
| **Environment** | show/set/unset manager environment variables |
| **Sessions** | List login sessions and users (loginctl) |
| **Interactive TUI** | Full dashboard powered by Ratatui (Rust rendering engine) |
| **Dual API** | Async-first + sync wrappers, identical interfaces |
| **Scope** | User session (`--user`) or system-wide (`--system`) |
| **Zero Dependencies** | Core library needs nothing beyond Python 3.11+ stdlib |

## Install

```bash
pip install systemd-client            # Core (zero deps)
pip install systemd-client[tui]       # + Interactive TUI (ratatui-py)
pip install systemd-client[dbus]      # + D-Bus backend (dasbus)
pip install systemd-client[all]       # Everything
```

## Quick Start

### Manage services

```python
from systemd_client import SystemdClient

with SystemdClient() as client:
    # List all running services
    for unit in client.list_units(unit_type="service"):
        print(f"{unit.name}: {unit.active_state} ({unit.sub_state})")

    # Get detailed status
    status = client.status("my-app.service")
    print(f"PID: {status.main_pid}, Since: {status.active_enter_timestamp}")

    # Control services
    client.restart("my-app.service")
    client.restart_units(["app.service", "worker.service"])  # batch

    # Quick checks
    print(f"Active: {client.is_active('my-app.service')}")
```

### Create services from Python

```python
from systemd_client import ServiceBuilder, TimerBuilder, SystemdClient

# Build a .service file with a fluent API
unit = (ServiceBuilder("my-app")
    .description("My FastAPI Application")
    .exec_start("/usr/bin/python3 /opt/app/main.py")
    .working_directory("/opt/app")
    .user("appuser")
    .environment({"PORT": "8080", "ENV": "production"})
    .restart("on-failure")
    .restart_sec(5)
    .wanted_by("default.target")
    .build())

# Deploy in one step
with SystemdClient() as client:
    client.install(unit)
    client.enable("my-app.service")
    client.start("my-app.service")

# Create a timer (cron replacement)
timer = (TimerBuilder("backup")
    .description("Daily backup")
    .on_calendar("*-*-* 02:00:00")
    .persistent(True)
    .wanted_by("timers.target")
    .build())
```

### Run transient units (systemd-run)

```python
with SystemdClient() as client:
    # One-off command as a systemd service
    result = client.run("/usr/bin/python3 /opt/backup.py", name="backup-task")
    print(f"Running: {result.unit_name}")

    # Schedule a recurring timer
    client.run_on_calendar("daily", "/usr/bin/python3 /opt/cleanup.py")

    # With resource limits
    client.run("make -j8", properties={"MemoryMax": "2G", "CPUQuota": "50%"})
```

### Monitor resources

```python
with SystemdClient() as client:
    # Set cgroup limits
    client.set_property("my-app.service", {"MemoryMax": "512M", "CPUQuota": "25%"})

    # Check resource usage
    usage = client.get_resource_usage("my-app.service")
    print(f"CPU: {usage.cpu_usage_nsec / 1e9:.1f}s")
    print(f"Memory: {usage.memory_current / 1024**2:.0f}MB")

    # List timers
    for timer in client.list_timers():
        print(f"{timer.name}: {timer.time_left}")
```

### Security analysis

```python
with SystemdClient() as client:
    # What's slow at boot?
    for entry in client.analyze_blame()[:5]:
        print(f"{entry.time_us / 1e6:.3f}s  {entry.unit}")

    # Security audit (0 = hardened, 10 = exposed)
    sec = client.analyze_security("my-app.service")
    print(f"Exposure: {sec.exposure}/10.0")

    # Verify unit files before deploying
    errors = client.analyze_verify("my-app.service")
```

### sd_notify — from your Python service

```python
# In a Type=notify systemd service:
from systemd_client.notify import SystemdNotifier

notifier = SystemdNotifier()
notifier.ready()                       # Tell systemd we're up
notifier.status("Listening on :8080")  # Update status text
notifier.watchdog()                    # Keep-alive ping
notifier.stopping()                    # Graceful shutdown
```

### Async API

```python
import asyncio
from systemd_client import AsyncSystemdClient

async def main():
    async with AsyncSystemdClient() as client:
        # Concurrent health check
        services = ["app.service", "worker.service", "scheduler.service"]
        results = await asyncio.gather(
            *(client.is_active(svc) for svc in services)
        )
        for svc, active in zip(services, results):
            print(f"{svc}: {'UP' if active else 'DOWN'}")

asyncio.run(main())
```

### System scope

```python
from systemd_client import SystemdClient, SystemdScope

# Manage system-wide services (requires root)
with SystemdClient(scope=SystemdScope.SYSTEM) as client:
    units = client.list_units(unit_type="service")
```

## CLI

```bash
# Unit management
systemd-client list --type service
systemd-client list-unit-files --state enabled
systemd-client status my-app.service
systemd-client cat my-app.service
systemd-client start my-app.service
systemd-client stop my-app.service
systemd-client restart a.service b.service c.service  # batch
systemd-client restart --no-block my-app.service
systemd-client try-restart my-app.service
systemd-client reload-or-restart my-app.service
systemd-client enable my-app.service
systemd-client reset-failed my-app.service
systemd-client kill my-app.service --signal SIGHUP

# Create and deploy unit files
systemd-client create-service --name my-app --exec-start /bin/app --restart on-failure --install
systemd-client create-timer --name backup --on-calendar daily --install
systemd-client install my-app.service --from-file ./my-app.service
systemd-client uninstall my-app.service

# Transient units (systemd-run)
systemd-client run /bin/echo hello --name my-task --wait
systemd-client run /opt/backup.py --on-calendar daily

# Resource monitoring
systemd-client resources my-app.service
systemd-client list-timers
systemd-client list-sockets
systemd-client list-dependencies my-app.service

# Analysis
systemd-client analyze-blame
systemd-client analyze-security my-app.service
systemd-client analyze-verify my-app.service

# Environment and sessions
systemd-client show-environment
systemd-client set-environment MY_VAR=hello
systemd-client list-sessions
systemd-client list-users

# Power management
systemd-client poweroff
systemd-client reboot
systemd-client suspend

# System scope
systemd-client --scope system list --type service
systemd-client --scope system restart nginx.service

# Interactive TUI dashboard
systemd-client tui
systemd-client --scope system tui

# Output formats
systemd-client --json list
systemd-client --no-color status my-app.service
```

## Interactive TUI

Launch the full interactive dashboard:

```bash
systemd-client tui
```

**Features:**
- Real-time unit list with color-coded states (green=active, red=failed)
- **Mouse support**: click to select, scroll wheel, tab clicks
- Keyboard: `s`=start, `S`=stop, `r`=restart, `e`=enable, `d`=disable, `j`=journal
- Type filters: `F1`=All, `F2`=Services, `F3`=Timers, `F4`=Sockets, `F5`=Failed
- Search: `/` to filter by name
- Journal panel at bottom with auto-refresh
- Scope toggle with `Tab`, 3 tabs: Dashboard, Timers, Help
- Powered by [Ratatui](https://ratatui.rs/) (Rust rendering engine, 30-60 FPS)

Requires: `pip install systemd-client[tui]`

## Architecture

```
Your Application
    |
    +-- SystemdClient (sync)
    |       |
    +-- AsyncSystemdClient (async)
            |
            +-- SubprocessBackend ---- systemctl --user/--system ----> systemd
            |     (default, zero deps)
            +-- DBusBackend ---------- D-Bus session/system bus ----> systemd
            |     (optional, dasbus)
            +-- AsyncJournalReader --- journalctl --output=json -----> journal
            +-- Builders ------------- .service/.timer/.socket/.path -> unit files
            +-- Analyze -------------- systemd-analyze ----------------> boot/security
            +-- Notify --------------- $NOTIFY_SOCKET -----------------> sd_notify
```

## Roadmap

### v1.0.0 — Production Ready

- [x] Unit management (list, status, start, stop, restart, reload, enable, disable, mask, unmask)
- [x] Unit File Builder (ServiceBuilder, TimerBuilder, SocketBuilder, PathBuilder)
- [x] Install / uninstall / edit (drop-in overrides)
- [x] Transient units (systemd-run, run_on_calendar)
- [x] Journal query with filters + real-time follow
- [x] Resource control (set_property, get_resource_usage)
- [x] List timers, sockets, dependencies
- [x] systemd-analyze (blame, security, verify, critical-chain)
- [x] sd_notify protocol (ready, status, watchdog, stopping)
- [x] Power management (poweroff, reboot, suspend, hibernate)
- [x] Environment management (show, set, unset)
- [x] Session management (list-sessions, list-users, loginctl)
- [x] Interactive TUI with Ratatui (mouse, keyboard, filters, journal)
- [x] Dual API (async + sync) with context managers
- [x] User + system scope
- [x] CLI with 32+ commands
- [x] Zero core dependencies
- [x] 286 tests, ruff clean, pyright strict
- [x] 13 documentation guides, 9 API references, 22 examples
- [ ] Integration tests with real systemd (create timer, verify, cleanup)
- [ ] Shell completions (bash, zsh, fish)
- [ ] TUI screenshots in README and docs
- [ ] Publish to awesome-python list

### v1.1.0 — Advanced Features

- [ ] D-Bus signals (PropertiesChanged watch for real-time monitoring without polling)
- [ ] `systemd-run --scope` (scope units)
- [ ] `systemctl edit --full` (replace entire unit file)
- [ ] `systemctl show` with specific property selection
- [ ] `list-dependencies --reverse`
- [ ] `--output=yaml` format
- [ ] Journal export to file
- [ ] Credential management (LoadCredential, SetCredential)

### v1.2.0 — Ecosystem

- [ ] systemd-tmpfiles wrapper (create, clean, remove)
- [ ] systemd-sysusers wrapper (user/group management)
- [ ] systemd-networkd integration
- [ ] systemd-resolved integration
- [ ] machinectl / systemd-nspawn container management
- [ ] coredumpctl integration

### v2.0.0 — Full Platform

- [ ] Remote systemd management (SSH + systemctl)
- [ ] Multi-host dashboard in TUI
- [ ] Ansible module compatibility
- [ ] Prometheus metrics exporter
- [ ] REST API server mode (`systemd-client serve`)
- [ ] Plugin system for custom backends

## Requirements

- Python >= 3.11
- Linux with systemd
- `systemctl` and `journalctl` on PATH

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and pull request process.

## License

[LGPL-2.1-or-later](LICENSE)

---

**systemd-client** · [Documentation](https://kalexnolasco.github.io/systemd-client/) · [GitHub](https://github.com/kalexnolasco/systemd-client) · [PyPI](https://pypi.org/project/systemd-client/)

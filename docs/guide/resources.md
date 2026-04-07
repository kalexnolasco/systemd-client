# Resource Control & Monitoring

systemd-client gives you full access to systemd's **cgroup-based resource control** and monitoring. Set memory limits, check CPU usage, list timers and sockets, inspect dependency trees, and send signals -- all from Python.

Let's walk through everything.

## Set Runtime Properties

Use `set_property()` to apply cgroup limits to a running unit without editing its unit file:

```python hl_lines="4 5 6 7 8"
from systemd_client import SystemdClient

client = SystemdClient()
client.set_property("my-app.service", {  # (1)!
    "MemoryMax": "512M",
    "CPUQuota": "25%",
    "TasksMax": "100",
})
```

1. These properties take effect **immediately** on the running unit. They persist until the unit is restarted (unless the unit file also sets them).

### Common Cgroup Properties

| Property | Example | Description |
|----------|---------|-------------|
| `MemoryMax` | `"512M"` | Hard memory ceiling (OOM-kill above this) |
| `MemoryHigh` | `"256M"` | Soft memory limit (throttling starts here) |
| `MemoryLow` | `"64M"` | Memory protection (won't be reclaimed below this) |
| `CPUQuota` | `"200%"` | CPU time quota (200% = 2 full cores) |
| `CPUWeight` | `"50"` | CPU scheduling weight (1-10000, default 100) |
| `TasksMax` | `"64"` | Maximum number of threads/processes |
| `IOWeight` | `"100"` | IO scheduling weight (1-10000) |
| `IOReadBandwidthMax` | `"/dev/sda 10M"` | Max read bandwidth per device |
| `IOWriteBandwidthMax` | `"/dev/sda 5M"` | Max write bandwidth per device |

!!! tip
    Use `MemoryHigh` for soft limits (systemd throttles the process) and `MemoryMax` for hard limits (systemd OOM-kills the process). In most cases, set both for graceful degradation.

### Example: Throttle a Runaway Service

```python hl_lines="3 4 5 6 7 8"
from systemd_client import SystemdClient

def throttle_service(unit_name: str) -> None:
    client = SystemdClient()
    client.set_property(unit_name, {
        "MemoryMax": "256M",
        "CPUQuota": "10%",
    })
    print(f"Throttled {unit_name}")

    # Verify the limits took effect
    usage = client.get_resource_usage(unit_name)
    if usage.memory_current:
        print(f"  Current memory: {usage.memory_current / 1024 / 1024:.1f}MB")
```

## Monitor Resource Usage

Read real-time resource usage for any unit with `get_resource_usage()`:

```python hl_lines="4 6 7 8 9 10 11"
from systemd_client import SystemdClient

client = SystemdClient()
usage = client.get_resource_usage("my-app.service")  # (1)!

if usage.cpu_usage_nsec is not None:
    print(f"CPU time:    {usage.cpu_usage_nsec / 1_000_000_000:.3f}s")  # (2)!
if usage.memory_current is not None:
    print(f"Memory:      {usage.memory_current / 1024 / 1024:.1f}MB")
if usage.memory_peak is not None:
    print(f"Memory peak: {usage.memory_peak / 1024 / 1024:.1f}MB")
if usage.tasks_current is not None:
    print(f"Tasks:       {usage.tasks_current}")
if usage.io_read_bytes is not None:
    print(f"IO read:     {usage.io_read_bytes / 1024:.0f}KB")
if usage.io_write_bytes is not None:
    print(f"IO write:    {usage.io_write_bytes / 1024:.0f}KB")
```

1. Returns a `ResourceUsage` frozen dataclass with all cgroup accounting fields.
2. CPU time is in nanoseconds -- divide by 1 billion for seconds.

```console
$ python resource_check.py
CPU time:    12.345s
Memory:      48.2MB
Memory peak: 128.5MB
Tasks:       8
IO read:     1024KB
IO write:    256KB
```

### ResourceUsage Fields

| Field | Type | Description |
|-------|------|-------------|
| `cpu_usage_nsec` | `int | None` | Total CPU time in nanoseconds |
| `memory_current` | `int | None` | Current memory usage in bytes |
| `memory_peak` | `int | None` | Peak memory usage in bytes |
| `tasks_current` | `int | None` | Current number of tasks (threads) |
| `io_read_bytes` | `int | None` | Total bytes read from disk |
| `io_write_bytes` | `int | None` | Total bytes written to disk |

!!! info
    Fields are `None` when cgroup accounting is not available for the unit (e.g., the unit is not running, or the cgroup controller is not enabled).

### Example: Resource Dashboard

```python hl_lines="7 8 9 10 11 12 13 14 15"
from systemd_client import SystemdClient

client = SystemdClient()
services = ["app.service", "worker.service", "scheduler.service"]

for name in services:
    try:
        usage = client.get_resource_usage(name)
        mem = f"{usage.memory_current / 1024 / 1024:.0f}MB" if usage.memory_current else "N/A"
        cpu = f"{usage.cpu_usage_nsec / 1e9:.1f}s" if usage.cpu_usage_nsec else "N/A"
        tasks = str(usage.tasks_current) if usage.tasks_current else "N/A"
        print(f"{name:<30} mem={mem:<8} cpu={cpu:<8} tasks={tasks}")
    except Exception as e:
        print(f"{name:<30} (error: {e})")
```

```console
$ python dashboard.py
app.service                    mem=48MB     cpu=12.3s    tasks=8
worker.service                 mem=128MB    cpu=45.6s    tasks=16
scheduler.service              mem=24MB     cpu=2.1s     tasks=3
```

## List Timers

Inspect all active timers with `list_timers()`:

```python hl_lines="4 6 7 8 9"
from systemd_client import SystemdClient

client = SystemdClient()
timers = client.list_timers()  # (1)!

for t in timers:
    activates = f" -> {t.activates}" if t.activates else ""
    left = f" ({t.time_left})" if t.time_left else ""
    print(f"{t.name}{activates}{left}")
```

1. Returns a `list[TimerInfo]` with next trigger time, time remaining, and the service each timer activates.

```console
$ python list_timers.py
backup.timer -> backup.service (2h 15min left)
cleanup.timer -> cleanup.service (45min left)
```

### TimerInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Timer unit name |
| `next_trigger` | `datetime | None` | Next scheduled trigger time |
| `time_left` | `str | None` | Human-readable time until next trigger |
| `last_trigger` | `datetime | None` | Last time the timer fired |
| `unit` | `str | None` | The unit this timer belongs to |
| `activates` | `str | None` | The service unit this timer activates |

## List Sockets

Inspect all active sockets with `list_sockets()`:

```python hl_lines="4 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
sockets = client.list_sockets()  # (1)!

for sock in sockets:
    print(f"{sock.name}: {sock.listen} ({sock.type})")
```

1. Returns a `list[SocketInfo]` with the listen address and socket type.

```console
$ python list_sockets.py
my-app.socket: /run/my-app.sock (Stream)
dbus.socket: /run/user/1000/bus (Stream)
```

### SocketInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Socket unit name |
| `listen` | `str` | Listen address (path or host:port) |
| `type` | `str` | Socket type (Stream, Datagram, etc.) |
| `unit` | `str` | Associated service unit |

## List Dependencies

Inspect the full dependency tree of a unit:

```python hl_lines="4"
from systemd_client import SystemdClient

client = SystemdClient()
deps = client.list_dependencies("my-app.service")  # (1)!

for dep in deps:
    print(f"  {dep}")
```

1. Returns a flat list of all units that this unit depends on (recursively). Equivalent to `systemctl list-dependencies`.

```console
$ python list_deps.py
  sysinit.target
  basic.target
  sockets.target
  paths.target
  timers.target
```

!!! tip
    Use dependency listing to understand startup ordering and debug "why does my service start before X?" issues.

## Send Signals with `kill()`

Send POSIX signals to all processes in a unit's cgroup:

```python hl_lines="4 7 10"
from systemd_client import SystemdClient

client = SystemdClient()

# Graceful reload (many daemons re-read config on SIGHUP)
client.kill("my-app.service", "SIGHUP")  # (1)!

# Graceful stop
client.kill("my-app.service", "SIGTERM")  # (2)!

# Force kill
client.kill("my-app.service", "SIGKILL")
```

1. Unlike `client.reload()`, this sends the signal directly to **all** processes in the cgroup, not just the main PID.
2. `SIGTERM` is the default if you omit the signal argument: `client.kill("my-app.service")`.

!!! warning
    `kill()` targets **every process** in the unit's cgroup. If the service has spawned child processes, they all receive the signal. Use `client.stop()` for normal shutdown -- it follows the unit's `ExecStop=` logic.

### When to Use `kill()` vs `stop()`

| Method | Use When |
|--------|----------|
| `client.stop()` | Normal shutdown. Runs `ExecStop=`, respects `TimeoutStopSec`. |
| `client.kill("...", "SIGHUP")` | Trigger a config reload without restart. |
| `client.kill("...", "SIGTERM")` | Bypass `ExecStop=` and signal all processes directly. |
| `client.kill("...", "SIGKILL")` | Emergency: force-kill everything in the cgroup. |

## Putting It Together: Resource Monitor

Here's a script that monitors resource usage and applies throttling when memory exceeds a threshold:

```python hl_lines="7 8 9 13 14 15 16 17"
from systemd_client import SystemdClient

def monitor_and_throttle(unit_name: str, memory_threshold_mb: int = 512) -> None:
    client = SystemdClient()
    usage = client.get_resource_usage(unit_name)

    if usage.memory_current is None:
        print(f"{unit_name}: no memory data available")
        return

    current_mb = usage.memory_current / 1024 / 1024

    if current_mb > memory_threshold_mb:
        print(f"{unit_name}: {current_mb:.0f}MB exceeds {memory_threshold_mb}MB threshold")
        client.set_property(unit_name, {
            "MemoryMax": f"{memory_threshold_mb}M",
            "CPUQuota": "50%",
        })
        print(f"  Applied memory cap and CPU throttle")
    else:
        print(f"{unit_name}: {current_mb:.0f}MB -- within limits")

monitor_and_throttle("my-app.service", memory_threshold_mb=256)
```

!!! check
    If the function applies limits, you'll see the throttling message. The limits take effect immediately.

## CLI Commands

All resource operations are available from the command line.

### Resource Usage

```console
$ systemd-client resources my-app.service
  CPU: 12.345s
  Memory: 48.2MB
  Memory peak: 128.5MB
  Tasks: 8
  IO read: 1024KB
  IO write: 256KB
```

### List Timers

```console
$ systemd-client list-timers
backup.timer -> backup.service (2h 15min left)
cleanup.timer -> cleanup.service (45min left)
```

### List Sockets

```console
$ systemd-client list-sockets
my-app.socket  /run/my-app.sock  Stream
dbus.socket    /run/user/1000/bus  Stream
```

### List Dependencies

```console
$ systemd-client list-dependencies my-app.service
  sysinit.target
  basic.target
  sockets.target
```

### Send a Signal

```console
$ systemd-client kill my-app.service --signal SIGHUP
Sent SIGHUP to my-app.service
```

### JSON Output

All listing commands support `--json` for scripting:

```console
$ systemd-client --json list-timers | jq '.[].name'
"backup.timer"
"cleanup.timer"

$ systemd-client --json resources my-app.service | jq '.memory_current'
50593792
```

!!! tip
    Pipe `--json` output to `jq` for precise data extraction in shell scripts and monitoring pipelines.

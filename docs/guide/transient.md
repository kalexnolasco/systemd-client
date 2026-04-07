# Transient Units

Transient units let you run commands under systemd **without creating permanent unit files**. Think of it as a managed `systemd-run` -- your process gets its own cgroup, journal logging, and resource limits, all cleaned up automatically when it exits.

Let's see how to use them from Python and the CLI.

## Basic Usage

The simplest case -- run a command as a transient service:

```python hl_lines="4"
from systemd_client import SystemdClient

client = SystemdClient()
result = client.run("/usr/bin/python3 /opt/scripts/cleanup.py")  # (1)!
print(f"Unit: {result.unit_name}")
print(f"PID:  {result.pid}")
```

1. Starts the command as a transient systemd service. Returns immediately with the unit name and PID.

```console
$ python run_cleanup.py
Unit: run-r8a3f9c1d4e.service
PID:  12345
```

!!! info
    The transient service gets a random name like `run-r8a3f9c1d4e.service` unless you specify one. It appears in `systemctl --user list-units` while running.

## Named Transient Units

Give your transient unit a meaningful name:

```python hl_lines="3"
result = client.run(
    "/usr/bin/python3 /opt/scripts/cleanup.py",
    name="cleanup-job",  # (1)!
)
print(f"Unit: {result.unit_name}")
```

1. The unit will be named `cleanup-job.service` -- much easier to find in logs and status checks.

```console
$ python run_named.py
Unit: cleanup-job.service
```

!!! tip
    Named transient units make it easy to check status, read journals, and manage the process: `client.status("cleanup-job.service")`, `client.journal("cleanup-job.service")`.

## Wait for Completion

By default, `run()` returns immediately. Pass `wait=True` to block until the command finishes:

```python hl_lines="4"
result = client.run(
    ["/usr/bin/python3", "/opt/scripts/migrate.py", "--apply"],  # (1)!
    name="db-migrate",
    wait=True,  # (2)!
)
print(f"Migration complete: {result.unit_name}")
```

1. You can pass the command as a list (like `subprocess.run`) or as a single string.
2. The call blocks until the transient service exits. If the process fails, you'll get an `UnitOperationError`.

!!! warning
    With `wait=True`, the call will block your thread until the command completes. For long-running tasks, consider using the [async client](async-client.md) with `await client.run(...)`.

## Resource Limits

Apply cgroup resource limits to the transient unit through the `properties` parameter:

```python hl_lines="4 5 6 7"
result = client.run(
    "/usr/bin/python3 /opt/scripts/heavy-etl.py",
    name="etl-job",
    properties={
        "MemoryMax": "512M",   # (1)!
        "CPUQuota": "50%",     # (2)!
        "TasksMax": "32",      # (3)!
    },
)
```

1. Hard memory limit -- the process gets OOM-killed if it exceeds 512 MB.
2. CPU quota -- the process can use at most 50% of one CPU core.
3. Maximum number of tasks (threads/processes) the unit can spawn.

### Common Properties

| Property | Example | Description |
|----------|---------|-------------|
| `MemoryMax` | `"512M"` | Hard memory ceiling |
| `MemoryHigh` | `"256M"` | Soft memory limit (throttling starts here) |
| `CPUQuota` | `"200%"` | CPU time quota (200% = 2 full cores) |
| `TasksMax` | `"64"` | Maximum number of threads/processes |
| `IOWeight` | `"100"` | IO scheduling weight (1-10000, default 100) |
| `LimitNOFILE` | `"65535"` | Max open file descriptors |

!!! tip
    These are the same properties you can set in a `[Service]` section or with `systemctl set-property`. They're applied through systemd's cgroup controller.

## Remain After Exit

Keep the transient unit around after the process exits -- useful for inspecting logs and exit status:

```python hl_lines="4"
result = client.run(
    "/usr/bin/python3 /opt/scripts/one-shot-task.py",
    name="one-shot",
    remain_after_exit=True,  # (1)!
)
```

1. After the process exits, the unit stays in `active (exited)` state instead of being cleaned up. You can inspect it with `client.status("one-shot.service")` and read its journal.

??? info "Cleaning up remain_after_exit units"

    To clean up a unit with `remain_after_exit`, stop it manually:

    ```python
    client.stop("one-shot.service")
    ```

    After stopping, the transient unit is removed automatically.

## Scheduled Tasks with `run_on_calendar()`

Create a transient **timer** that runs a command on a schedule:

```python hl_lines="1 2 3 4"
result = client.run_on_calendar(
    "*-*-* 02:00:00",  # (1)!
    "/usr/bin/python3 /opt/scripts/nightly-backup.py",
    name="nightly-backup",
)
print(f"Timer: {result.unit_name}")
```

1. Standard systemd calendar syntax. This runs every day at 2:00 AM.

Common calendar expressions:

| Expression | Meaning |
|------------|---------|
| `"hourly"` | Every hour on the hour |
| `"daily"` | Every day at midnight |
| `"weekly"` | Every Monday at midnight |
| `"*:0/15"` | Every 15 minutes |
| `"Mon,Fri *-*-* 09:00"` | Monday and Friday at 9 AM |
| `"*-*-* 02:00:00"` | Every day at 2:00 AM |

!!! info
    The transient timer creates **two** units: a `.timer` and a `.service`. The timer triggers the service on schedule. Both are cleaned up when you stop or disable the timer.

### Transient Timer Example: Log Rotation

```python hl_lines="5 6 7 8 9 12"
from systemd_client import SystemdClient

client = SystemdClient()

# Rotate logs every 6 hours
result = client.run_on_calendar(
    "*-*-* 0/6:00:00",
    ["/usr/bin/find", "/var/log/my-app", "-name", "*.log",
     "-mtime", "+7", "-delete"],
    name="log-cleanup",
)
print(f"Scheduled: {result.unit_name}")

# Verify it's in the timer list
for timer in client.list_timers():
    print(f"  {timer.name}: next trigger in {timer.time_left}")
```

## Putting It Together: Sandboxed Task Runner

Here's a pattern for running untrusted or resource-intensive tasks safely:

```python hl_lines="6 7 8 9 10 11 12 13 17 22"
from systemd_client import SystemdClient, UnitOperationError

def run_sandboxed(command: str, memory_limit: str = "256M") -> bool:
    client = SystemdClient()

    try:
        result = client.run(
            command,
            name="sandboxed-task",
            wait=True,
            properties={
                "MemoryMax": memory_limit,
                "CPUQuota": "100%",
                "TasksMax": "16",
            },
        )
    except UnitOperationError as e:
        print(f"Task failed: {e.detail}")

        # Check the journal for details
        for entry in client.journal("sandboxed-task.service", lines=10):
            print(f"  {entry.message}")
        return False

    print(f"Task completed: {result.unit_name}")
    return True

run_sandboxed("/usr/bin/python3 /opt/scripts/process-data.py")
```

!!! check
    If the function prints `Task completed: ...`, the sandboxed task ran successfully within its resource limits.

## CLI: `systemd-client run`

All transient operations are available from the command line too.

### Run a Command

```console
$ systemd-client run -- /usr/bin/python3 /opt/scripts/cleanup.py
Running: run-r8a3f9c1d4e.service (PID 12345)
```

### Named, with Wait

```console
$ systemd-client run --name my-task --wait -- /usr/bin/python3 script.py
Running: my-task.service (PID 12346)
```

### With Resource Limits

```console
$ systemd-client run --property MemoryMax=512M --property CPUQuota=50% --name etl -- python3 etl.py
Running: etl.service (PID 12347)
```

### Remain After Exit

```console
$ systemd-client run --name one-shot --remain-after-exit -- python3 task.py
Running: one-shot.service (PID 12348)
```

### Scheduled Timer

```console
$ systemd-client run --on-calendar daily --name nightly-backup -- /opt/scripts/backup.sh
Scheduled timer: nightly-backup.timer
```

!!! tip
    Combine `--on-calendar` with `--name` for easily identifiable scheduled tasks. You can then check on them with `systemd-client list-timers`.

# Unit File Builder

systemd-client includes **fluent builders** for creating `.service`, `.timer`, `.socket`, and `.path` unit files from Python. No more hand-editing INI files -- build them with type-safe method chains, validate automatically, and install with one call.

Let's walk through everything the builders can do.

## ServiceBuilder

The most common builder. Let's create a complete service unit file:

```python hl_lines="3 5 6 7 8 9 10 11 12 13"
from systemd_client import ServiceBuilder

unit = (
    ServiceBuilder("my-app")
    .description("My Application Server")  # (1)!
    .type_("simple")
    .exec_start("/usr/bin/python3 /opt/my-app/server.py")
    .restart("on-failure")  # (2)!
    .restart_sec(5)
    .user("myuser")
    .group("mygroup")
    .working_directory("/opt/my-app")
    .environment({"PORT": "8080", "LOG_LEVEL": "info"})  # (3)!
    .wanted_by("default.target")  # (4)!
    .build()  # (5)!
)

print(unit.content)
```

1. Sets the `Description=` in the `[Unit]` section.
2. Restart policy: `"no"`, `"on-success"`, `"on-failure"`, `"on-abnormal"`, `"on-watchdog"`, `"on-abort"`, or `"always"`.
3. Pass a dict -- it renders as `Environment="PORT=8080" "LOG_LEVEL=info"`.
4. The `[Install]` section determines what `systemctl enable` hooks into.
5. `.build()` validates all fields and returns a `UnitFile` frozen dataclass.

This generates:

```ini
[Unit]
Description=My Application Server

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/my-app/server.py
Restart=on-failure
RestartSec=5
User=myuser
Group=mygroup
WorkingDirectory=/opt/my-app
Environment="PORT=8080" "LOG_LEVEL=info"

[Install]
WantedBy=default.target
```

!!! check
    The generated content is valid systemd syntax, ready to install.

### All ServiceBuilder Methods

The builder supports every common `[Service]` directive:

```python hl_lines="3 4 5 6 9 10 13 14 15 16 19 20 21"
builder = ServiceBuilder("my-app")

# Command lifecycle
builder.exec_start("/usr/bin/my-app")
builder.exec_start_pre("/usr/bin/my-app --check")
builder.exec_start_post("/usr/bin/notify-ready")
builder.exec_stop("/usr/bin/my-app --shutdown")
builder.exec_stop_post("/usr/bin/cleanup")
builder.exec_reload("/bin/kill -HUP $MAINPID")

# Restart behavior
builder.restart("on-failure")
builder.restart_sec(5)
builder.timeout_start_sec(30)
builder.timeout_stop_sec(30)
builder.watchdog_sec(60)

# Identity & paths
builder.user("deploy")
builder.group("deploy")
builder.working_directory("/opt/my-app")
builder.environment_file("/opt/my-app/.env")
builder.runtime_directory("my-app")
builder.state_directory("my-app")
builder.syslog_identifier("my-app")

# Security hardening
builder.private_tmp(True)
builder.protect_system("strict")
builder.protect_home("yes")
builder.dynamic_user(True)

# Miscellaneous
builder.remain_after_exit(True)
builder.nice(-5)
builder.limit_nofile(65535)
builder.standard_output("journal")
builder.standard_error("journal")
builder.pid_file("/run/my-app/my-app.pid")
```

### Unit Section Methods

All builders share these `[Unit]` section methods:

```python hl_lines="1 2 3 4 5 6 7 8"
builder.description("My service")
builder.documentation("https://docs.example.com")
builder.after("network.target", "postgresql.service")  # (1)!
builder.before("shutdown.target")
builder.requires("postgresql.service")  # (2)!
builder.wants("redis.service")  # (3)!
builder.binds_to("my-db.service")
builder.conflicts("my-old-app.service")
builder.condition_path_exists("/opt/my-app/config.toml")
```

1. Ordering: start this unit **after** the listed targets/services.
2. Hard dependency: if PostgreSQL fails, this unit fails too.
3. Soft dependency: start Redis if available, but don't fail if it's missing.

## TimerBuilder

Create systemd timers to schedule recurring tasks:

```python hl_lines="3 5 6 7 8"
from systemd_client import TimerBuilder

unit = (
    TimerBuilder("my-backup")
    .description("Daily backup job")
    .on_calendar("*-*-* 02:00:00")  # (1)!
    .persistent(True)  # (2)!
    .unit("my-backup.service")  # (3)!
    .wanted_by("timers.target")
    .build()
)
```

1. Standard systemd calendar syntax. Other examples: `"daily"`, `"hourly"`, `"Mon *-*-* 09:00"`, `"*:0/15"` (every 15 minutes).
2. If the machine was off when the timer should have fired, run it immediately on next boot.
3. Explicit target service. If omitted, systemd looks for `my-backup.service` (same base name).

??? tip "Other timer triggers..."

    Besides `on_calendar()`, you can use monotonic timers:

    ```python hl_lines="2 3 4 5"
    builder = TimerBuilder("my-watchdog")
    builder.on_boot_sec(120)           # 120 seconds after boot
    builder.on_startup_sec(60)         # 60 seconds after systemd start
    builder.on_unit_active_sec(300)    # 300 seconds after the service last started
    builder.on_unit_inactive_sec(600)  # 600 seconds after the service last stopped
    builder.accuracy_sec(60)           # Allow 60s jitter (saves power)
    builder.randomized_delay_sec(30)   # Random delay up to 30s (prevents thundering herd)
    ```

!!! info
    The timer builder requires **at least one** time trigger (`on_calendar`, `on_boot_sec`, etc.). Calling `.build()` without one raises `UnitFileValidationError`.

## SocketBuilder

Create socket-activated services:

```python hl_lines="3 5 6 7 8"
from systemd_client import SocketBuilder

unit = (
    SocketBuilder("my-app")
    .description("My App Socket")
    .listen_stream(8080)  # (1)!
    .accept(False)  # (2)!
    .service("my-app.service")
    .wanted_by("sockets.target")
    .build()
)
```

1. Pass a port number for TCP or a path string for a Unix socket (e.g., `"/run/my-app.sock"`).
2. `accept=False` means systemd passes the socket to a single service instance. `accept=True` spawns a new instance per connection.

### Other Socket Directives

```python hl_lines="1 2 3 4 5 6"
builder.listen_datagram(9090)                     # UDP socket
builder.listen_sequential_packet("/run/my.sock")  # SOCK_SEQPACKET
builder.listen_fifo("/run/my-app.fifo")           # Named pipe
builder.socket_user("www-data")
builder.socket_group("www-data")
builder.socket_mode("0660")
builder.max_connections(64)
builder.keep_alive(True)
```

!!! info
    The socket builder requires **at least one** listen directive. Calling `.build()` without one raises `UnitFileValidationError`.

## PathBuilder

Trigger a service when a file or directory changes:

```python hl_lines="3 5 6 7 8"
from systemd_client import PathBuilder

unit = (
    PathBuilder("config-watcher")
    .description("Watch config for changes")
    .path_changed("/etc/my-app/config.toml")  # (1)!
    .unit("my-app-reload.service")  # (2)!
    .make_directory(True)
    .wanted_by("default.target")
    .build()
)
```

1. Triggers when the file is closed after a write. Other options: `path_exists()`, `path_exists_glob()`, `path_modified()`, `directory_not_empty()`.
2. The service to activate when the path condition is met.

### All Path Directives

```python hl_lines="1 2 3 4 5"
builder.path_exists("/var/lock/deploy.lock")        # Trigger when file appears
builder.path_exists_glob("/var/spool/mail/*")        # Glob pattern
builder.path_changed("/etc/my-app/config.toml")     # File written and closed
builder.path_modified("/etc/my-app/config.toml")    # File modified (inotify)
builder.directory_not_empty("/var/spool/my-queue")   # Directory has files
builder.trigger_limit_interval_sec(10)               # Rate limit: interval
builder.trigger_limit_burst(5)                       # Rate limit: max triggers
```

!!! warning
    All path arguments **must be absolute paths**. Relative paths cause a `UnitFileValidationError` at build time.

## Template Units

All builders support **template** units -- units with an `@` suffix that can be instantiated with different parameters:

```python hl_lines="1 2"
unit = (
    ServiceBuilder("my-worker", template=True)  # (1)!
    .description("Worker instance %i")  # (2)!
    .exec_start("/usr/bin/python3 /opt/workers/%i.py")
    .restart("on-failure")
    .wanted_by("default.target")
    .build()
)

print(unit.name)  # "my-worker@.service"
```

1. `template=True` generates a filename like `my-worker@.service`.
2. Use `%i` in directives to reference the instance identifier. When you enable `my-worker@fast.service`, `%i` becomes `fast`.

!!! tip
    Template units are powerful for running multiple instances of the same service with different configurations. Enable them with: `client.enable("my-worker@instance1.service")`.

## Installing Unit Files

Once you've built a unit file, install it with the client:

```python hl_lines="7 8"
from systemd_client import SystemdClient, ServiceBuilder

client = SystemdClient()

unit = ServiceBuilder("my-app").exec_start("/usr/bin/my-app").build()

path = client.install(unit)  # (1)!
print(f"Installed to: {path}")
```

1. Writes the unit file to the appropriate directory (`~/.config/systemd/user/` for user scope, `/etc/systemd/system/` for system scope). Returns the full path.

### Uninstalling

```python hl_lines="1"
client.uninstall("my-app.service")  # (1)!
```

1. Removes the unit file and runs `daemon-reload` automatically.

### Drop-in Overrides with `edit()`

Override specific directives without replacing the entire unit file:

```python hl_lines="1 2 3 4 5 6"
path = client.edit("my-app.service", {  # (1)!
    "Service": {
        "Environment": '"LOG_LEVEL=debug"',
        "MemoryMax": "512M",
    },
})
print(f"Override written to: {path}")
```

1. Creates a drop-in file at `~/.config/systemd/user/my-app.service.d/override.conf`. This is the same thing `systemctl edit` does.

The drop-in file will contain:

```ini
[Service]
Environment="LOG_LEVEL=debug"
MemoryMax=512M
```

!!! tip
    Drop-in overrides let you customize vendor-provided units without modifying the original file. Your changes survive package updates.

## Validation Errors

All builders validate required fields when you call `.build()`. If something is missing, you get a `UnitFileValidationError`:

```python hl_lines="6 8 9"
from systemd_client import ServiceBuilder, UnitFileValidationError

try:
    unit = ServiceBuilder("my-app").build()  # (1)!
except UnitFileValidationError as e:
    print(f"Unit: {e.builder_name}")
    for error in e.errors:
        print(f"  - {error}")
```

1. This fails because `ExecStart` is required for service units.

```console
$ python validate.py
Unit: my-app.service
  - ExecStart is required for service units
```

Each builder has its own validation rules:

| Builder | Required |
|---------|----------|
| `ServiceBuilder` | `exec_start()` |
| `TimerBuilder` | At least one time trigger (`on_calendar`, `on_boot_sec`, etc.) |
| `SocketBuilder` | At least one listen directive (`listen_stream`, `listen_datagram`, etc.) |
| `PathBuilder` | At least one path directive (`path_changed`, `path_exists`, etc.) |

!!! warning
    `PathBuilder` also validates that all path arguments are **absolute paths**. `WorkingDirectory` on `ServiceBuilder` has the same check.

## Full Deploy Workflow

Here's the recommended pattern: build the unit, install it, reload systemd, enable, and start:

```python hl_lines="8 15 18 21 24 27"
from systemd_client import (
    SystemdClient,
    ServiceBuilder,
    UnitFileValidationError,
    UnitOperationError,
)

def deploy_service(name: str, exec_cmd: str) -> bool:
    client = SystemdClient()

    # 1. Build the unit file
    unit = (
        ServiceBuilder(name)
        .description(f"{name} application server")
        .exec_start(exec_cmd)
        .restart("on-failure")
        .restart_sec(5)
        .environment({"ENV": "production"})
        .wanted_by("default.target")
        .build()
    )

    # 2. Install
    path = client.install(unit)  # (1)!
    print(f"Installed to {path}")

    # 3. Reload daemon
    client.daemon_reload()  # (2)!

    # 4. Enable (start on boot)
    result = client.enable(f"{name}.service")  # (3)!
    for change in result.changes:
        print(f"  {change[0]} {change[1]} -> {change[2]}")

    # 5. Start
    try:
        client.start(f"{name}.service")
    except UnitOperationError as e:
        print(f"Start failed: {e.detail}")
        return False

    # 6. Verify
    if client.is_active(f"{name}.service"):
        status = client.status(f"{name}.service")
        print(f"Running with PID {status.main_pid}")
        return True

    print("Service did not become active")
    return False

deploy_service("my-app", "/usr/bin/python3 /opt/my-app/server.py")
```

1. Writes the `.service` file to the user unit directory.
2. Tells systemd to re-read all unit files from disk.
3. Creates the symlink so the service starts automatically on login/boot.

!!! check
    If you see `Running with PID ...`, the full build-install-enable-start cycle completed successfully.

??? info "Teardown: uninstalling a service"

    To reverse the deploy, disable, stop, and uninstall:

    ```python hl_lines="1 2 3 4"
    client.stop("my-app.service")
    client.disable("my-app.service")
    client.uninstall("my-app.service")
    # daemon_reload is called automatically by uninstall()
    ```

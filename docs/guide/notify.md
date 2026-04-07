# sd_notify Protocol

The `SystemdNotifier` class implements the `sd_notify(3)` protocol in **pure Python** -- no C bindings, no extra dependencies. Use it to tell systemd when your service is ready, update the status text, send watchdog pings, and signal graceful shutdown.

Let's walk through the full protocol.

## The SystemdNotifier Class

```python hl_lines="3 5"
from systemd_client.notify import SystemdNotifier

notifier = SystemdNotifier()  # (1)!

if notifier.available:  # (2)!
    print("Running under systemd Type=notify")
else:
    print("Not running under systemd (no $NOTIFY_SOCKET)")
```

1. Reads `$NOTIFY_SOCKET` from the environment. If the variable is set, the notifier sends datagrams over the Unix socket. If not, all methods silently return `False`.
2. The `available` property checks whether `$NOTIFY_SOCKET` is set. Useful for code that runs both under systemd and standalone.

!!! info
    `SystemdNotifier` is safe to use in **any** environment. When `$NOTIFY_SOCKET` is not set (e.g., during development or testing), all notification methods return `False` and do nothing. You never need to conditionally import or guard against it.

## Notification Methods

### `ready()` -- Service Startup Complete

Tell systemd that your service has finished initializing and is ready to serve:

```python hl_lines="5"
from systemd_client.notify import SystemdNotifier

notifier = SystemdNotifier()
# ... perform initialization, bind ports, connect to database ...
notifier.ready()  # (1)!
```

1. Sends `READY=1`. For `Type=notify` services, systemd waits for this before considering the service "active". Without it, the service stays in "activating" state until `TimeoutStartSec` expires.

!!! warning
    For `Type=notify` services, you **must** call `ready()` after initialization completes. If you forget, systemd will kill the service after the startup timeout.

### `status()` -- Update Status Text

Set the status text that appears in `systemctl status`:

```python hl_lines="1 2 3"
notifier.status("Listening on :8080")  # (1)!
notifier.status("Processing 42 requests/sec")
notifier.status("Shutting down, 3 connections remaining")
```

1. Sends `STATUS=<text>`. The text appears in the `Status:` line of `systemctl status my-app.service`.

```console
$ systemctl --user status my-app.service
  Active: active (running) since ...
  Status: "Processing 42 requests/sec"
    Main PID: 12345 (python3)
```

!!! tip
    Update the status text throughout the lifecycle of your service. It makes debugging much easier -- you can see at a glance what the service is currently doing.

### `watchdog()` -- Keep-Alive Ping

Send a watchdog keep-alive to prevent systemd from restarting your service:

```python hl_lines="5"
import time

notifier.ready()
while running:
    notifier.watchdog()  # (1)!
    do_work()
    time.sleep(10)
```

1. Sends `WATCHDOG=1`. Must be sent at intervals shorter than `WatchdogSec` in the unit file. If systemd doesn't receive a ping within the window, it considers the service hung and restarts it.

!!! info
    The watchdog is only active when `WatchdogSec=` is set in the unit file. If it's not set, calling `watchdog()` has no effect (but also no harm).

### `stopping()` -- Graceful Shutdown

Notify systemd that the service is beginning its shutdown sequence:

```python hl_lines="2"
def shutdown():
    notifier.stopping()  # (1)!
    close_connections()
    flush_buffers()
    cleanup_resources()
```

1. Sends `STOPPING=1`. Tells systemd the service is shutting down intentionally. systemd will wait for the process to exit (up to `TimeoutStopSec`) before force-killing it.

### `reloading()` -- Configuration Reload

Signal that the service is reloading its configuration:

```python hl_lines="2 5"
def reload_config():
    notifier.reloading()  # (1)!
    load_config_from_disk()
    apply_new_config()
    notifier.ready()  # (2)!
```

1. Sends `RELOADING=1`. systemd changes the service state to "reloading".
2. After the reload completes, send `READY=1` again to transition back to "active".

### Other Methods

```python hl_lines="1 2 3"
notifier.errno(5)                # Report error number (EIO)
notifier.mainpid(12345)          # Report the main PID
notifier.extend_timeout(5000000) # Request 5 more seconds for startup/shutdown
```

### Raw Notifications

For advanced use cases, send arbitrary notification strings:

```python hl_lines="1"
notifier.notify("READY=1\nSTATUS=Custom message")  # (1)!
```

1. The `notify()` method accepts any newline-separated key=value string, following the `sd_notify(3)` protocol specification.

## Complete Methods Reference

| Method | Notification Sent | Description |
|--------|-------------------|-------------|
| `ready()` | `READY=1` | Service startup complete |
| `status(text)` | `STATUS=<text>` | Update the status text shown in `systemctl status` |
| `stopping()` | `STOPPING=1` | Service is beginning shutdown |
| `reloading()` | `RELOADING=1` | Service is reloading configuration |
| `watchdog()` | `WATCHDOG=1` | Watchdog keep-alive ping |
| `errno(n)` | `ERRNO=<n>` | Report an errno-style error number |
| `mainpid(pid)` | `MAINPID=<pid>` | Report the main PID of the service |
| `extend_timeout(usec)` | `EXTEND_TIMEOUT_USEC=<usec>` | Request more time during startup/shutdown |
| `notify(state)` | `<state>` | Send any raw sd_notify string |
| `close()` | -- | Close the notification socket |

All methods return `bool`: `True` if the notification was sent, `False` if `$NOTIFY_SOCKET` is not set or sending failed.

## Example: Full Type=notify Service

Here's a complete example with the unit file and Python code working together.

### The Unit File

Build it with `ServiceBuilder` or write it by hand:

=== "Builder"

    ```python hl_lines="4 5 6 7 8 9"
    from systemd_client import ServiceBuilder

    unit = (
        ServiceBuilder("my-app")
        .description("My Application Server")
        .type_("notify")  # (1)!
        .exec_start("/usr/bin/python3 /opt/my-app/server.py")
        .watchdog_sec(30)  # (2)!
        .restart("on-failure")
        .wanted_by("default.target")
        .build()
    )
    ```

    1. `Type=notify` tells systemd to wait for `READY=1` before marking the service as active.
    2. If the service doesn't send `WATCHDOG=1` within 30 seconds, systemd restarts it.

=== "Unit File"

    ```ini hl_lines="2 4"
    [Unit]
    Description=My Application Server

    [Service]
    Type=notify
    ExecStart=/usr/bin/python3 /opt/my-app/server.py
    WatchdogSec=30
    Restart=on-failure

    [Install]
    WantedBy=default.target
    ```

### The Python Service

```python title="server.py" hl_lines="7 8 13 18 22 26"
import signal
import time

from systemd_client.notify import SystemdNotifier

notifier = SystemdNotifier()
running = True

def handle_sigterm(signum, frame):
    global running
    running = False

# Initialize
print("Starting up...")
time.sleep(2)  # Simulate slow initialization

# Tell systemd we're ready
notifier.ready()  # (1)!
notifier.status("Listening on :8080")

# Main loop
while running:
    notifier.watchdog()  # (2)!
    # ... handle requests ...
    time.sleep(10)

# Graceful shutdown
notifier.stopping()  # (3)!
notifier.status("Shutting down...")
print("Cleaning up...")
time.sleep(1)
notifier.close()
```

1. After initialization completes, tell systemd the service is ready. The unit transitions from "activating" to "active".
2. Send a watchdog ping every iteration. As long as the loop runs, the service stays alive. If the loop hangs, systemd will restart the service after `WatchdogSec` (30s).
3. Tell systemd we're shutting down intentionally -- not crashing.

!!! check
    With this setup, `systemctl status my-app.service` shows the real-time status text, and the watchdog automatically restarts the service if it hangs.

## Power Management

The `SystemdClient` also provides power management methods that interact with `systemctl`:

```python hl_lines="4 5 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
client.poweroff()   # Shut down the system
client.reboot()     # Reboot the system
client.suspend()    # Suspend to RAM
client.hibernate()  # Hibernate to disk
```

!!! warning
    Power management commands require appropriate privileges. On most systems, you need root access or a polkit rule that authorizes the calling user. These commands are **immediate** -- they do not prompt for confirmation.

??? tip "System scope is not required"

    Power management commands work from **both** user and system scope clients. They map directly to `systemctl poweroff`, `systemctl reboot`, etc.

### CLI

```console
$ systemd-client poweroff
Poweroff initiated

$ systemd-client reboot
Reboot initiated

$ systemd-client suspend
Suspend initiated

$ systemd-client hibernate
Hibernate initiated
```

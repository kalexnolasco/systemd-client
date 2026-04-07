# sd_notify Protocol

Notify systemd about your Python service's state. Pure Python, zero dependencies.

## Usage in a Type=notify Service

```ini title="my-app.service"
[Service]
Type=notify
ExecStart=/usr/bin/python3 /opt/app/main.py
WatchdogSec=30
```

```python title="main.py" hl_lines="1 4-5 9 12"
from systemd_client.notify import SystemdNotifier

notifier = SystemdNotifier()
notifier.ready()                        # (1)!
notifier.status("Listening on :8080")   # (2)!

# In your main loop:
while running:
    notifier.watchdog()                 # (3)!
    handle_requests()

notifier.stopping()                     # (4)!
```

1. Tell systemd the service is ready. Required for `Type=notify`.
2. Update the status text visible in `systemctl status`.
3. Send watchdog keep-alive. Must be sent before `WatchdogSec` expires.
4. Tell systemd the service is shutting down gracefully.

## All Methods

| Method | Notification | Description |
|--------|-------------|-------------|
| `ready()` | `READY=1` | Service startup complete |
| `status(text)` | `STATUS=...` | Update status text |
| `stopping()` | `STOPPING=1` | Service is stopping |
| `reloading()` | `RELOADING=1` | Reloading configuration |
| `watchdog()` | `WATCHDOG=1` | Keep-alive ping |
| `errno(n)` | `ERRNO=n` | Report error number |
| `mainpid(pid)` | `MAINPID=pid` | Report main PID |
| `extend_timeout(usec)` | `EXTEND_TIMEOUT_USEC=...` | Request more startup time |

!!! info
    `SystemdNotifier` gracefully handles non-systemd environments. All methods return `False` if `$NOTIFY_SOCKET` is not set.

## Power Management

```python
with SystemdClient() as client:
    client.poweroff()    # systemctl poweroff
    client.reboot()      # systemctl reboot
    client.suspend()     # systemctl suspend
    client.hibernate()   # systemctl hibernate
```

!!! warning
    Power management commands require appropriate privileges.

## CLI

```bash
systemd-client poweroff
systemd-client reboot
systemd-client suspend
systemd-client hibernate
```

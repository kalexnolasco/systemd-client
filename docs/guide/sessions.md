# Environment & Sessions

systemd-client gives you access to the **systemd manager environment** and **logind session management**. Set environment variables that affect all future units, list active login sessions, and manage user sessions -- all from Python.

Let's walk through everything.

## Environment Variables

The systemd manager maintains its own set of environment variables. These are inherited by all units it starts. You can view, set, and unset them at runtime.

### Show the Current Environment

```python hl_lines="4 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
env = client.show_environment()  # (1)!

for key, value in sorted(env.items()):
    print(f"{key}={value}")
```

1. Returns a `dict[str, str]` of all environment variables set in the systemd manager. This is the equivalent of `systemctl --user show-environment`.

```console
$ python show_env.py
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
HOME=/home/myuser
LANG=en_US.UTF-8
PATH=/usr/local/bin:/usr/bin:/bin
XDG_RUNTIME_DIR=/run/user/1000
```

### Set Environment Variables

Add or override environment variables in the manager. All units started after this point inherit the new values:

```python hl_lines="4 5 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
client.set_environment({  # (1)!
    "MY_APP_ENV": "production",
    "MY_APP_DEBUG": "0",
})
```

1. Pass a dict of key-value pairs. Existing variables with the same name are overwritten.

!!! tip
    This is useful for setting variables that multiple services need without editing each unit file individually. For example, set `DATABASE_URL` once and all services pick it up.

### Unset Environment Variables

Remove variables from the manager environment:

```python hl_lines="4"
from systemd_client import SystemdClient

client = SystemdClient()
client.unset_environment(["MY_APP_ENV", "MY_APP_DEBUG"])  # (1)!
```

1. Pass a list of variable names to remove. It is not an error to unset a variable that doesn't exist.

### Example: Configure and Verify

```python hl_lines="5 6 7 8 10 11 12 13 16"
from systemd_client import SystemdClient

client = SystemdClient()

# Set deployment variables
client.set_environment({
    "DEPLOY_ENV": "staging",
    "LOG_LEVEL": "debug",
})

# Verify they're set
env = client.show_environment()
print(f"DEPLOY_ENV = {env.get('DEPLOY_ENV', 'NOT SET')}")
print(f"LOG_LEVEL  = {env.get('LOG_LEVEL', 'NOT SET')}")

# Clean up after deployment
client.unset_environment(["DEPLOY_ENV", "LOG_LEVEL"])
```

!!! warning
    Environment changes are **not persistent** across manager restarts. They last only for the current session. For permanent environment variables, use `Environment=` or `EnvironmentFile=` directives in unit files, or configure them in `~/.config/environment.d/`.

## Login Sessions

systemd-client wraps `loginctl` to list and manage login sessions. This is useful for monitoring who is logged in and managing their sessions programmatically.

### List Sessions

```python hl_lines="4 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
sessions = client.list_sessions()  # (1)!

for s in sessions:
    print(f"  Session {s.id}: {s.user} (uid={s.uid}) tty={s.tty} state={s.state}")
```

1. Returns a `list[SessionInfo]`. Each session represents an active login (console, SSH, graphical, etc.).

```console
$ python list_sessions.py
  Session 1: myuser (uid=1000) tty=tty1 state=active
  Session 3: myuser (uid=1000) tty=pts/0 state=active
  Session 5: admin (uid=1001) tty=pts/1 state=active
```

### SessionInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Session identifier (e.g., `"1"`, `"3"`) |
| `uid` | `int` | User ID |
| `user` | `str` | Username |
| `seat` | `str` | Seat name (e.g., `"seat0"`) or empty |
| `tty` | `str` | TTY or pseudo-terminal (e.g., `"tty1"`, `"pts/0"`) |
| `state` | `str` | Session state (e.g., `"active"`, `"online"`, `"closing"`) |

### List Users

See all currently logged-in users:

```python hl_lines="4 6 7"
from systemd_client import SystemdClient

client = SystemdClient()
users = client.list_users()  # (1)!

for u in users:
    print(f"  {u.uid}: {u.name} ({u.state})")
```

1. Returns a `list[UserInfo]` with one entry per logged-in user (even if they have multiple sessions).

```console
$ python list_users.py
  1000: myuser (active)
  1001: admin (active)
```

### UserInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `uid` | `int` | User ID |
| `name` | `str` | Username |
| `state` | `str` | User state (e.g., `"active"`, `"lingering"`) |

## Session Control

### Terminate a Session

Forcibly end a login session:

```python hl_lines="4"
from systemd_client import SystemdClient

client = SystemdClient()
client.terminate_session("3")  # (1)!
```

1. Terminates the session with the given ID. All processes belonging to the session are killed.

!!! warning
    Terminating a session **kills all processes** belonging to that session, including any running applications. Make sure you target the correct session ID.

### Lock a Session

Lock a session's screen (for graphical sessions):

```python hl_lines="4"
from systemd_client import SystemdClient

client = SystemdClient()
client.lock_session("3")  # (1)!
```

1. Sends a lock signal to the session. For graphical sessions, this typically activates the screen locker. For text sessions, the behavior depends on the session's lock handler.

## Putting It Together: Session Audit

Here's a script that audits active sessions and their users:

```python hl_lines="6 7 8 9 10 11 17 18 19 20"
from systemd_client import SystemdClient

def session_audit() -> None:
    client = SystemdClient()

    # List users
    users = client.list_users()
    print(f"Logged-in users: {len(users)}")
    for u in users:
        print(f"  {u.name} (uid={u.uid}, state={u.state})")

    print()

    # List sessions with details
    sessions = client.list_sessions()
    print(f"Active sessions: {len(sessions)}")
    for s in sessions:
        seat_info = f" seat={s.seat}" if s.seat else ""
        tty_info = f" tty={s.tty}" if s.tty else ""
        print(f"  [{s.id}] {s.user}{tty_info}{seat_info} ({s.state})")

    # Check for idle sessions
    idle = [s for s in sessions if s.state != "active"]
    if idle:
        print(f"\n{len(idle)} non-active session(s) found:")
        for s in idle:
            print(f"  Session {s.id} ({s.user}): {s.state}")

session_audit()
```

!!! check
    This script gives you a snapshot of who is logged in, through which terminals, and which sessions might be idle.

## CLI Commands

All environment and session operations are available from the command line.

### Environment

```console
$ systemd-client show-environment
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
HOME=/home/myuser
LANG=en_US.UTF-8
PATH=/usr/local/bin:/usr/bin:/bin
```

```console
$ systemd-client set-environment MY_VAR=hello DEBUG=1
Set 2 variable(s)
```

```console
$ systemd-client unset-environment MY_VAR DEBUG
Unset 2 variable(s)
```

### Sessions

```console
$ systemd-client list-sessions
  1  myuser (uid=1000)  tty1  active
  3  myuser (uid=1000)  pts/0  active
```

```console
$ systemd-client list-users
  1000  myuser  active
  1001  admin  active
```

### JSON Output

Both session commands support `--json` for scripting:

```console
$ systemd-client --json list-sessions | jq '.[].user'
"myuser"
"admin"

$ systemd-client --json show-environment | jq '.HOME'
"/home/myuser"
```

!!! tip
    The JSON output from `show-environment` is a flat object, making it easy to extract individual variables with `jq`.

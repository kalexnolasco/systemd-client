# Environment & Sessions

Manage systemd environment variables and login sessions.

## Environment Variables

```python hl_lines="4 7 10"
from systemd_client import SystemdClient

with SystemdClient() as client:
    # Show current environment
    env = client.show_environment()
    for key, value in sorted(env.items()):
        print(f"{key}={value}")

    # Set variables
    client.set_environment({"MY_VAR": "hello", "DEBUG": "1"})

    # Unset variables
    client.unset_environment(["MY_VAR", "DEBUG"])
```

## Login Sessions

List active login sessions (equivalent to `loginctl list-sessions`):

```python
for session in client.list_sessions():
    print(f"  {session.id}: {session.user} (uid={session.uid}) {session.tty}")
```

## List Users

```python
for user in client.list_users():
    print(f"  {user.uid}: {user.name} ({user.state})")
```

## Session Control

```python
client.terminate_session("3")   # End a session
client.lock_session("3")        # Lock a session
```

!!! warning
    Session operations may require root privileges.

## CLI

```bash
systemd-client show-environment
systemd-client set-environment MY_VAR=hello DEBUG=1
systemd-client unset-environment MY_VAR DEBUG
systemd-client list-sessions
systemd-client list-users
```

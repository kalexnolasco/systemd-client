# CLI

systemd-client ships with a **command-line interface** that acts as a typed, colored wrapper around `systemctl` and `journalctl`.

Let's see what it can do.

## Installation

The CLI is included automatically when you install the package -- no extras needed:

```console
$ pip install systemd-client
$ systemd-client --version
systemd-client 0.2.0
```

!!! check
    If you see a version number, the CLI is ready to go.

## List Units

Start by seeing what units are running:

```console
$ systemd-client list
```

You can filter the results by type, state, or both:

```console
$ systemd-client list --type service
$ systemd-client list --type timer
$ systemd-client list --state active
$ systemd-client list --state failed
```

!!! tip
    Combine `--type` and `--state` to narrow things down fast. For example, `systemd-client list --type service --state failed` shows only failed services.

## List Unit Files

See all **installed** unit files, including those not currently loaded:

```console
$ systemd-client list-unit-files
$ systemd-client list-unit-files --type service
$ systemd-client list-unit-files --state enabled
```

!!! info
    `list-unit-files` shows everything installed, while `list` only shows currently loaded units. Use `list-unit-files` to discover disabled or masked services.

## Unit Status

Get detailed information about a specific unit:

```console
$ systemd-client status my-app.service
```

This shows the same kind of information you'd see from `systemctl status`, but parsed and formatted.

## Show Unit File Content

View the content of a unit file:

```console
$ systemd-client cat my-app.service
```

## Unit Operations

Start, stop, restart, or reload a unit:

```console
$ systemd-client start my-app.service
$ systemd-client stop my-app.service
$ systemd-client restart my-app.service
$ systemd-client reload my-app.service
```

### Batch Operations

Pass multiple unit names to operate on them at once:

```console
$ systemd-client start app.service worker.service scheduler.service
$ systemd-client restart app.service worker.service
```

### Non-Blocking Mode

Use `--no-block` to return immediately without waiting for the operation to complete:

```console
$ systemd-client start --no-block my-app.service
```

### Try-Restart and Reload-or-Restart

```console
$ systemd-client try-restart my-app.service
$ systemd-client reload-or-restart my-app.service
```

!!! info
    `try-restart` only restarts if the unit is currently active. `reload-or-restart` reloads if the unit supports it, otherwise restarts.

### Enable and Disable

Control whether a unit starts on boot:

```console
$ systemd-client enable my-app.service
$ systemd-client disable my-app.service
```

### Mask and Unmask

Prevent a unit from being started at all:

```console
$ systemd-client mask my-app.service
$ systemd-client unmask my-app.service
```

!!! warning
    Masking a unit **prevents it from starting** -- even manually. Use this when you want to completely block a unit from running.

### Daemon Reload

After editing a `.service` file, tell systemd to pick up the changes:

```console
$ systemd-client daemon-reload
```

### Reset Failed

Clear the failed state for a unit, or all units:

```console
$ systemd-client reset-failed my-app.service
$ systemd-client reset-failed
```

## Journal

The journal commands wrap `journalctl --user` with a friendlier interface.

### Basic Usage

```console
$ systemd-client journal
```

!!! info
    By default, this shows the last **25** entries.

### Filter by Unit

```console
$ systemd-client journal --unit my-app.service
$ systemd-client journal -u my-app.service
```

### Number of Lines

```console
$ systemd-client journal -n 100
```

### Time Range

```console
$ systemd-client journal --since "1h ago"
$ systemd-client journal --since "2025-01-01" --until "2025-01-02"
```

### Priority Filter

```console
$ systemd-client journal --priority warning
$ systemd-client journal -p err
```

### Grep Pattern

```console
$ systemd-client journal --grep "error|timeout"
$ systemd-client journal -g "connection refused"
```

### Follow (Real-Time)

```console
$ systemd-client journal --follow
$ systemd-client journal -u my-app.service -f
```

!!! tip
    Combine flags for precise results. For example, follow only error-level logs from a specific service:

    ```console
    $ systemd-client journal -u my-app.service -f -p err
    ```

## Global Flags

These flags work with **any** command:

| Flag | Description |
|------|-------------|
| `--scope user\|system` | Scope: user session or system-wide (default: `user`) |
| `--backend auto\|subprocess\|dbus` | Backend selection (default: `auto`) |
| `--json` | Output as JSON instead of table |
| `--no-color` | Disable ANSI color codes |
| `--version` | Show version and exit |

### System Scope

By default, all commands operate on the **user session**. To manage **system services**, use `--scope system`:

```console
$ systemd-client --scope system list --type service
$ systemd-client --scope system status nginx.service
$ systemd-client --scope system restart nginx.service
```

!!! warning
    System scope operations typically require root privileges (or appropriate polkit rules).

### JSON Output

The `--json` flag is perfect for scripting and piping into other tools:

```console hl_lines="1 4"
$ systemd-client --json list | jq '.[] | select(.active_state == "failed")'

$ systemd-client --json journal -u my-app.service -n 10
```

??? tip "Other options for processing JSON output..."

    You can use any JSON processing tool:

    ```console
    $ systemd-client --json list | python -m json.tool
    $ systemd-client --json journal -u my-app.service | jq length
    ```

### No Color

Useful when piping output or writing to files:

```console
$ systemd-client --no-color list > services.txt
```

!!! info
    Color is also automatically disabled when stdout is not a terminal (e.g., when piping).

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (unit not found, operation failed, etc.) |
| `130` | Interrupted (Ctrl+C) |

!!! note
    In shell scripts, you can check the exit code to determine if an operation succeeded:

    ```console
    $ systemd-client restart my-app.service && echo "Restarted!" || echo "Failed!"
    ```

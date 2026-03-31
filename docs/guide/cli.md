# CLI

systemd-client includes a command-line interface that acts as a typed, colored wrapper around `systemctl --user` and `journalctl --user`.

## Installation

The CLI is included when you install the package:

```bash
pip install systemd-client
systemd-client --version
```

## Commands

### List units

```bash
# All units
systemd-client list

# Filter by type
systemd-client list --type service
systemd-client list --type timer

# Filter by state
systemd-client list --state active
systemd-client list --state failed
```

### Unit status

```bash
systemd-client status my-app.service
```

### Unit operations

```bash
systemd-client start my-app.service
systemd-client stop my-app.service
systemd-client restart my-app.service
systemd-client reload my-app.service
```

### Enable / disable

```bash
systemd-client enable my-app.service
systemd-client disable my-app.service
systemd-client mask my-app.service
systemd-client unmask my-app.service
```

### Daemon reload

```bash
systemd-client daemon-reload
```

### Journal

```bash
# Last 25 entries (default)
systemd-client journal

# Filter by unit
systemd-client journal --unit my-app.service
systemd-client journal -u my-app.service

# Number of lines
systemd-client journal -n 100

# Time range
systemd-client journal --since "1h ago"
systemd-client journal --since "2024-01-01" --until "2024-01-02"

# Priority filter
systemd-client journal --priority warning
systemd-client journal -p err

# Grep pattern
systemd-client journal --grep "error|timeout"
systemd-client journal -g "connection refused"

# Follow (real-time)
systemd-client journal --follow
systemd-client journal -u my-app.service -f
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--backend auto\|subprocess\|dbus` | Backend selection (default: auto) |
| `--json` | Output as JSON instead of table |
| `--no-color` | Disable ANSI color codes |
| `--version` | Show version and exit |

### JSON output

```bash
# Pipe to jq for processing
systemd-client --json list | jq '.[] | select(.active_state == "failed")'

# Journal as JSON
systemd-client --json journal -u my-app.service -n 10
```

### No color

Useful for piping or scripts:

```bash
systemd-client --no-color list > services.txt
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (unit not found, operation failed, etc.) |
| `130` | Interrupted (Ctrl+C) |

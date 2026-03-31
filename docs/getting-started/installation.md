# Installation

## Requirements

| Requirement | Detail |
|-------------|--------|
| **Python** | >= 3.11 |
| **OS** | Linux with systemd |
| **System tools** | `systemctl` and `journalctl` on PATH |

## Install from PyPI

```bash
pip install systemd-client
```

## Optional Extras

=== "D-Bus backend"

    For direct D-Bus communication instead of subprocess calls:

    ```bash
    pip install systemd-client[dbus]
    ```

    Requires `libdbus` system library.

=== "Pydantic models"

    For Pydantic BaseModel variants of the data models:

    ```bash
    pip install systemd-client[pydantic]
    ```

=== "Everything"

    ```bash
    pip install systemd-client[all]
    ```

## Development Install

```bash
git clone https://github.com/kalexnolasco/systemd-client.git
cd systemd-client
pip install -e ".[dev]"
```

## Verify Installation

```bash
python -c "from systemd_client import SystemdClient; print('OK')"
```

Or try the CLI:

```bash
systemd-client --version
systemd-client list
```

## System Requirements

### systemd user session

The library uses `systemctl --user` and `journalctl --user`. Verify your user session is active:

```bash
systemctl --user status
```

If you get "Failed to connect to bus", enable linger:

```bash
loginctl enable-linger $(whoami)
```

!!! important
    `loginctl enable-linger` is required for user services to run when the user is not logged in (e.g., after SSH disconnect).

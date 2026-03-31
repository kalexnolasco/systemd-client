# Installation

Let's get `systemd-client` installed and verify everything is working.

## 1. Install the package

The simplest way to install `systemd-client` is with `pip`:

```console
$ pip install systemd-client
```

That's it. The base package has **zero dependencies** -- it talks to systemd through
`systemctl` and `journalctl` subprocesses, so nothing extra is needed.

!!! check "Zero dependencies"
    The core library requires no third-party packages at all. Python 3.11+ and a
    Linux system with systemd are all you need.

## 2. Pick your extras

Depending on your use case, you might want one of the optional extras.

### D-Bus backend

```console
$ pip install "systemd-client[dbus]"
```

This installs [`dasbus`](https://pypi.org/project/dasbus/) so the client can talk
to systemd over D-Bus directly, instead of spawning `systemctl` processes.

!!! info "System library required"
    The `dbus` extra requires `libdbus` to be installed on your system.
    On Debian/Ubuntu: `sudo apt install libdbus-1-dev`. On Fedora/RHEL: `sudo dnf install dbus-devel`.

### Pydantic models

```console
$ pip install "systemd-client[pydantic]"
```

This gives you Pydantic `BaseModel` variants of all data models, useful if you're
building a FastAPI or other Pydantic-centric application.

### Everything

```console
$ pip install "systemd-client[all]"
```

Installs both `dasbus` and `pydantic` in one go.

??? info "What each extra installs"
    | Extra | Packages | Purpose |
    |-------|----------|---------|
    | `dbus` | `dasbus>=1.7` | Direct D-Bus communication with systemd |
    | `pydantic` | `pydantic>=2.0` | Pydantic BaseModel variants of data models |
    | `all` | Both of the above | Everything |

## 3. Development install from Git

If you want to contribute or hack on the library itself, clone the repo and install
in editable mode with the `dev` extras:

```console
$ git clone https://github.com/kalexnolasco/systemd-client.git
$ cd systemd-client
$ pip install -e ".[dev]"
```

!!! tip
    The `dev` extra includes `pytest`, `ruff`, `pyright`, and `coverage` --
    everything you need to run the test suite and linters.

## 4. Check it

Now let's verify the installation works. Open your terminal and run:

```console
$ python -c "from systemd_client import SystemdClient; print('OK')"
OK
```

!!! check "You should see"
    ```
    OK
    ```
    If you get an `ImportError`, make sure you installed the package in the correct
    Python environment (check `which python` and `pip list | grep systemd`).

Now try the CLI:

```console
$ systemd-client --version
systemd-client 0.1.2
```

And list your running user services:

```console
$ systemd-client list --type service
```

You should see a colored table of your systemd user services. If you see output
like this, everything is working:

```
UNIT                          LOAD   ACTIVE   SUB       DESCRIPTION
my-app.service                loaded active   running   My Application
dbus.service                  loaded active   running   D-Bus User Message Bus
...
```

## System requirements

Before you go further, let's make sure your system is ready.

| Requirement | Detail |
|-------------|--------|
| **Python** | >= 3.11 |
| **OS** | Linux with systemd |
| **System tools** | `systemctl` and `journalctl` on `PATH` |

!!! warning "Linux only"
    `systemd-client` only works on Linux. It will not work on macOS, Windows, or
    WSL1 (WSL2 is fine if you have systemd enabled).

### systemd user session

The library uses `systemctl --user` and `journalctl --user` by default. Let's
verify your user session is active:

```console
$ systemctl --user status
```

!!! check "You should see"
    Something like:
    ```
    ● hostname
        State: running
        Units: 123 loaded (incl. loaded), 45 running
         Jobs: 0 queued
       ...
    ```

If you get **"Failed to connect to bus"**, your user session might not be running.
This commonly happens in SSH sessions or containers. The fix is to enable "linger":

```console
$ loginctl enable-linger $(whoami)
```

!!! tip "What does `enable-linger` do?"
    Normally, systemd user sessions are started when a user logs in and stopped when
    they log out. `loginctl enable-linger` tells systemd to start your user session
    at boot and keep it running even when you're not logged in. This is **required**
    if you want your user services to survive SSH disconnects, run in CI/CD, or
    start at boot time.

??? warning "Containers and minimal environments"
    Some container images (e.g., `python:3.12-slim`) don't ship with systemd at all.
    If you're running inside a container, you need a systemd-enabled base image and
    the container must be started with the appropriate privileges (e.g.,
    `--privileged` or `--cgroupns=host`).

## Next steps

Now that you're installed and verified, head to the **[First Steps](quickstart.md)**
tutorial to write your first script with `systemd-client`.

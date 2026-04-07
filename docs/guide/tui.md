# Interactive TUI

systemd-client ships with a full **interactive terminal dashboard** powered by [Ratatui](https://ratatui.rs/) -- a Rust rendering engine that gives you 30-60 FPS terminal graphics. Browse units, start/stop services, read journals, and inspect timers -- all from a single terminal window.

Let's get it running.

## Installation

The TUI requires the `ratatui-py` package, which is included as an optional dependency:

```console hl_lines="1"
$ pip install systemd-client[tui]  # (1)!
```

1. This installs `ratatui-py` alongside `systemd-client`. The Rust rendering library is bundled as a pre-compiled binary.

!!! info
    The `[tui]` extra installs `ratatui-py`, which bundles a pre-compiled Rust library. No Rust toolchain is needed on your machine.

??? tip "Already installed systemd-client without the TUI?"

    Just install the extra:

    ```console
    $ pip install systemd-client[tui]
    ```

    This adds `ratatui-py` without reinstalling the rest of the package.

## Launch

Start the TUI from the command line:

```console hl_lines="1"
$ systemd-client tui
```

By default, it shows **user session** services. To manage **system** services:

```console hl_lines="1"
$ systemd-client --scope system tui  # (1)!
```

1. System scope shows units managed by the system instance of systemd (PID 1), such as `nginx.service`, `sshd.service`, etc.

!!! warning
    System scope typically requires root privileges. Use `sudo` or run as root when needed.

You can also specify a backend:

```console
$ systemd-client --backend subprocess tui
```

### Programmatic Launch

You can also launch the TUI from Python code:

```python hl_lines="3 4 5"
from systemd_client.tui._app import run_tui
from systemd_client.enums import BackendType, SystemdScope

exit_code = run_tui(  # (1)!
    backend=BackendType.AUTO,
    scope=SystemdScope.USER,
)
```

1. Returns `0` on normal exit, `1` if it could not load units. The function blocks until the user presses `q`.

!!! check
    If the TUI launches and you see a unit table with colored status indicators, everything is working.

## Dashboard Layout

The TUI has **three tabs**, switched with the `1`, `2`, and `3` keys.

### Tab 1 -- Dashboard (Default)

The main view. It's divided into four panels:

| Panel | Position | Contents |
|-------|----------|----------|
| **Unit Table** | Left (60%) | All units with name, load state, active state, sub-state, and description. Color-coded by status. |
| **Detail** | Top-right | Detailed info about the currently selected unit: state icon, load state, description. |
| **Actions** | Mid-right | Quick reference of available keyboard shortcuts for unit operations. |
| **Journal** | Bottom (full width) | Journal entries for the selected unit. Appears when you press `j`. Auto-refreshes every 2 seconds. |

The **header bar** at the top shows:

- Total unit count
- Active count (green)
- Failed count (red, if any)
- Inactive count (gray)
- Current scope badge (USER or SYSTEM)

The **footer bar** shows a compact keyboard shortcut reference.

### Tab 2 -- Timers

A table of all active timers showing:

| Column | Description |
|--------|-------------|
| TIMER | Timer unit name |
| TIME LEFT | Human-readable time until next trigger |
| ACTIVATES | The service unit the timer will start |

!!! info
    Timer data is loaded when you switch to the Timers tab. It refreshes alongside the regular unit refresh (every 2 seconds).

### Tab 3 -- Help

A comprehensive reference of all keyboard shortcuts, organized into sections: Navigation, Type Filters, Unit Operations, and Journal.

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `Up` / `Down` | Move selection up/down one row |
| `PgUp` / `PgDn` | Move selection 10 rows up/down |
| `Home` / `End` | Jump to the first/last unit |
| `1` `2` `3` | Switch between Dashboard, Timers, and Help tabs |
| `Tab` | Toggle between user and system scope |
| `q` | Quit the TUI |
| `Esc` | Clear active filter, or quit if no filter is set |

### Type Filters

Quickly narrow the unit table to a specific type:

| Key | Filter |
|-----|--------|
| `F1` | Show **all** units (clear type filter) |
| `F2` | Show only `.service` units |
| `F3` | Show only `.timer` units |
| `F4` | Show only `.socket` units |
| `F5` | Show only **failed** units (any type) |

!!! tip
    Type filters combine with the search filter. Press `F2` to show only services, then `/` to search within those services.

### Search Filter

| Key | Action |
|-----|--------|
| `/` | Enter search mode |
| *type text* | Filter units by name (case-insensitive) |
| `Enter` | Confirm the filter and exit search mode |
| `Esc` | Clear the filter and exit search mode |

The search filter appears in the unit table title, e.g., `Units [service /my-app] (3)`.

### Unit Operations

These work on the **currently selected unit** in the Dashboard tab:

| Key | Action |
|-----|--------|
| `s` | **Start** the selected unit |
| `S` | **Stop** the selected unit |
| `r` | **Restart** the selected unit |
| `e` | **Enable** the selected unit |
| `d` | **Disable** the selected unit |
| `R` | **Reload** the systemd daemon (`daemon-reload`) |
| `F` | **Reset failed** state of the selected unit |
| `j` | Load/refresh the **journal** for the selected unit |

After each operation, the Detail panel shows a confirmation message:

- `OK: Started my-app.service` (green)
- `Error: Unit not found` (yellow)

!!! info
    Operations trigger an immediate unit list refresh so you can see the result right away. The journal panel also auto-refreshes every 2 seconds when active.

### Journal Panel

Press `j` on any unit to open the journal panel at the bottom of the Dashboard:

- Shows the **last 50** journal entries for the selected unit
- Entries are **color-coded** by priority: red for ERR and below, yellow for WARNING, white for INFO and above
- Timestamps are shown in `HH:MM:SS` format
- The panel title shows the unit name: `Journal: my-app.service`
- Auto-refreshes every 2 seconds alongside the unit list

!!! tip
    The journal panel is great for watching service startup in real-time. Press `j` right after pressing `s` (start) to follow the boot sequence.

## Scope Toggle

Press `Tab` to switch between **user** and **system** scope:

- The header badge changes from `USER` (green) to `SYSTEM` (yellow)
- The unit list reloads with units from the new scope
- The client is reconnected to the appropriate scope
- A `Scope: system` confirmation message appears in the Detail panel

!!! warning
    Switching to system scope may require elevated privileges. If the TUI cannot read system units, you will see an error message.

## Color Coding

The TUI uses consistent color coding throughout:

| Color | Meaning |
|-------|---------|
| **Green** | Active / running |
| **Red** | Failed |
| **Gray** | Inactive / dead |
| **Yellow** | Activating / deactivating / reloading / warnings |
| **Cyan** | Accent (headers, selected elements, shortcuts) |
| **White** | Normal text |

The currently selected row is highlighted with a `>>` prefix and inverted colors (cyan background, black text).

## Mouse Support

The TUI supports full mouse interaction:

| Action | Effect |
|--------|--------|
| **Left click** on unit table | Select that unit |
| **Scroll wheel** in table | Navigate up/down (3 rows per scroll) |
| **Left click** on tab bar | Switch to that tab |

!!! info
    Mouse tracking is enabled automatically when the TUI starts and disabled on exit. Works in most modern terminal emulators (GNOME Terminal, Konsole, Alacritty, kitty, iTerm2, etc.).

## Auto-Refresh

The TUI refreshes automatically:

- **Unit list**: Every 2 seconds (every 4th tick at 500ms tick rate)
- **Journal**: Every 2 seconds (when a journal is loaded)
- **Timers**: On tab switch and during regular refreshes

!!! info
    The refresh happens in the background. If a refresh fails (e.g., due to a transient D-Bus error), the TUI silently retries on the next cycle.

## Example Workflows

### Monitor a Deployment

1. Launch: `systemd-client tui`
2. Press `F2` to filter to services only
3. Press `/` and type `my-app` to find your service
4. Press `Enter` to confirm the filter
5. Press `j` to open the journal panel
6. Press `r` to restart the service
7. Watch the journal for startup messages

### Find Failed Units

1. Launch: `systemd-client tui`
2. Press `F5` to filter to failed units only
3. Select a failed unit with `Up`/`Down`
4. Press `j` to see what went wrong in the journal
5. Press `F` to reset the failed state
6. Press `s` to start the unit again

### Compare User and System Services

1. Launch: `systemd-client tui`
2. Browse your user services
3. Press `Tab` to switch to system scope
4. Press `F2` to see only system services
5. Press `Tab` again to switch back to user scope

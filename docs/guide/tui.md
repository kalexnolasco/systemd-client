# Interactive TUI

A full interactive dashboard powered by [Ratatui](https://ratatui.rs/) (Rust rendering engine).

## Installation

```bash
pip install systemd-client[tui]
```

## Launch

```bash
systemd-client tui
systemd-client --scope system tui    # System services
```

## Dashboard Layout

The TUI has three tabs:

**Tab 1 — Dashboard** (default):

- **Left**: Unit table with real-time status (color-coded)
- **Top-right**: Detail panel for selected unit
- **Mid-right**: Actions panel with keybindings
- **Bottom**: Journal panel (loads when you press `j`)

**Tab 2 — Timers**: Active timers with next trigger info

**Tab 3 — Help**: All keyboard shortcuts

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move selection up/down |
| `PgUp` / `PgDn` | Move 10 items |
| `Home` / `End` | Jump to first/last |
| `1` `2` `3` | Switch tabs |
| `Tab` | Toggle user/system scope |
| `q` / `Esc` | Quit |

### Type Filters

| Key | Filter |
|-----|--------|
| `F1` | Show all units |
| `F2` | Show `.service` only |
| `F3` | Show `.timer` only |
| `F4` | Show `.socket` only |
| `F5` | Show failed only |

### Search

| Key | Action |
|-----|--------|
| `/` | Enter search mode |
| Type text | Filter by name |
| `Enter` | Confirm filter |
| `Esc` | Clear filter |

### Unit Operations

| Key | Action |
|-----|--------|
| `s` | Start selected unit |
| `S` | Stop selected unit |
| `r` | Restart selected unit |
| `e` | Enable selected unit |
| `d` | Disable selected unit |
| `R` | Daemon reload |
| `F` | Reset failed state |
| `j` | Load journal (bottom panel, auto-refreshes) |

## Features

- **Real-time**: Units and journal auto-refresh every 2 seconds
- **Color-coded**: Green = active, Red = failed, Gray = inactive
- **Selection highlight**: `>>` prefix + inverted colors on selected row
- **Journal panel**: Shows last 50 entries with priority coloring
- **Scope toggle**: Switch between user and system services with `Tab`
- **Powered by Ratatui**: 30-60 FPS Rust rendering engine

# Changelog

## v0.2.0

Major feature release: system scope, new operations, context managers, and bug fixes.

### New Features

- **System scope support**: `SystemdScope.USER` / `SystemdScope.SYSTEM` parameter on clients, journal, and CLI (`--scope system`)
- **Context manager protocol**: `async with AsyncSystemdClient()` and `with SystemdClient()` for proper resource cleanup
- **`list_unit_files()`**: List all installed unit files (including disabled/masked), equivalent to `systemctl list-unit-files`
- **`cat()`**: Show unit file content, equivalent to `systemctl cat`
- **`reset_failed()`**: Reset failed state for a unit or all units
- **`try_restart()`**: Restart only if the unit is currently active
- **`reload_or_restart()`**: Reload if supported, otherwise restart
- **Batch operations**: `start_units()`, `stop_units()`, `restart_units()` for operating on multiple units at once
- **`--no-block` mode**: Fire-and-forget operations that return immediately without waiting
- **`UnitFileInfo` model**: New frozen dataclass for unit file information (name, state, preset)
- **`__repr__`** on clients: Shows backend and scope for easier debugging
- **Coverage in CI**: Test coverage reporting with 80% minimum threshold

### Bug Fixes

- **Fix `_safe_int` for exit codes**: `ExecMainStatus=0` (success) was incorrectly returned as `None`. PID=0 remains `None`.
- **DBus backend timestamps**: `get_unit_status()` now reads `ActiveEnterTimestamp`, `ActiveExitTimestamp`, `InactiveEnterTimestamp`, `InactiveExitTimestamp`
- **DBus backend `exec_main_status`**: Now correctly reads and returns the exit code

### CLI

- New `--scope user|system` global flag
- New subcommands: `list-unit-files`, `cat`, `reset-failed`
- New operations: `try-restart`, `reload-or-restart`
- `--no-block` flag for start/stop/restart/reload operations
- Batch support: pass multiple unit names to start/stop/restart (e.g., `systemd-client start a.service b.service`)

### Breaking Changes

- Backend constructors now accept `scope` parameter
- `JournalQuery` has a new `scope` field
- Minimum version bumped to 0.2.0

### Internal

- Generic `run_sync()` with proper `TypeVar` typing
- `AbstractBackend.close()` method for resource cleanup
- 149 unit tests (up from 89)

## v0.1.2

- Add MkDocs documentation site with Material theme
- Fix Key Features rendering on docs homepage
- Add Documentation URL to PyPI metadata

## v0.1.1

- Fix README rendering on PyPI (replace Mermaid with ASCII diagram, add dynamic badges)
- Lint fixes (ruff autofix)

## v0.1.0

Initial release.

- `SystemdClient` and `AsyncSystemdClient` with full unit management API
- Subprocess backend (default, zero dependencies)
- D-Bus backend via dasbus (optional)
- Journal reader with query filters and real-time follow
- Frozen dataclass models: `UnitInfo`, `UnitStatus`, `JournalEntry`, `EnableResult`
- StrEnum types: `ActiveState`, `LoadState`, `UnitFileState`, `SubState`, `UnitType`, `JournalPriority`, `BackendType`
- Exception hierarchy with `SystemdClientError` base
- CLI with table and JSON output
- Optional Pydantic model variants
- PEP 561 typed package
- 89 unit tests
- 15 copy-paste examples

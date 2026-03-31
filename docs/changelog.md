# Changelog

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

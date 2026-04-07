# Contributing to systemd-client

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/kalexnolasco/systemd-client.git
cd systemd-client
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev,tui]"
```

## Running Tests

```bash
pytest tests/ -v                    # Run all tests
pytest tests/ -v --tb=short         # Short tracebacks
coverage run -m pytest tests/       # With coverage
coverage report --fail-under=80     # Check coverage
```

## Code Quality

```bash
ruff check src/ tests/              # Lint
ruff check src/ tests/ --fix        # Auto-fix
pyright src/                        # Type checking
```

## Code Style

- **Python 3.11+** required
- **ruff** for linting (E, F, W, I, UP, B, SIM, TCH, RUF rules)
- **pyright** strict mode for type checking
- Frozen dataclasses with `slots=True` for models
- `StrEnum` for enumerations
- `from __future__ import annotations` in every file
- Google-style docstrings
- Line length: 100 characters

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure `ruff check` and `pytest` pass
5. Submit a PR with a clear description

## Architecture

```
src/systemd_client/
├── client.py           # AsyncSystemdClient + SystemdClient
├── models.py           # Frozen dataclasses
├── enums.py            # StrEnum definitions
├── exceptions.py       # Exception hierarchy
├── notify.py           # sd_notify protocol
├── _analyze.py         # systemd-analyze wrapper
├── _sync.py            # Async-to-sync bridge
├── backends/           # Pluggable backends (subprocess, dbus)
├── builders/           # Unit file builders (service, timer, socket, path)
├── cli/                # CLI entry point + formatters
├── journal/            # Journal reader + query builder
└── tui/                # Interactive TUI (ratatui-py)
```

## Adding a New Feature

1. Add model(s) to `models.py` if needed
2. Add enum(s) to `enums.py` if needed
3. Add abstract method to `backends/_base.py`
4. Implement in `backends/_subprocess.py` and `backends/_dbus.py`
5. Add client method to `client.py` (both async and sync)
6. Add CLI subcommand to `cli/_app.py`
7. Write tests
8. Update documentation

## License

By contributing, you agree that your contributions will be licensed under the LGPL-2.1-or-later license.

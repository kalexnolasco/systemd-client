# Analyze API

Functions wrapping `systemd-analyze` for boot analysis, security scoring,
unit verification, and critical-chain inspection.

These are available as methods on `SystemdClient` / `AsyncSystemdClient`
(e.g., `client.analyze_blame()`), but are implemented in the
`systemd_client._analyze` module.

## Module functions

::: systemd_client._analyze
    options:
      members:
        - analyze_blame
        - analyze_critical_chain
        - analyze_security
        - analyze_verify

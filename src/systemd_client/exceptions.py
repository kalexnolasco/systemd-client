"""Exception hierarchy for systemd-client."""

from __future__ import annotations


class SystemdClientError(Exception):
    """Base exception for all systemd-client errors."""


class UnitNotFoundError(SystemdClientError):
    """Raised when a unit is not found."""

    def __init__(self, unit_name: str) -> None:
        self.unit_name = unit_name
        super().__init__(f"Unit not found: {unit_name}")


class UnitOperationError(SystemdClientError):
    """Raised when a unit operation fails."""

    def __init__(self, unit_name: str, operation: str, detail: str) -> None:
        self.unit_name = unit_name
        self.operation = operation
        self.detail = detail
        super().__init__(f"Failed to {operation} {unit_name}: {detail}")


class BackendError(SystemdClientError):
    """Base exception for backend-related errors."""


class BackendNotAvailableError(BackendError):
    """Raised when a requested backend is not available."""

    def __init__(self, backend: str, reason: str) -> None:
        self.backend = backend
        self.reason = reason
        super().__init__(f"Backend '{backend}' not available: {reason}")


class SubprocessError(BackendError):
    """Raised when a subprocess command fails unexpectedly."""

    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Command {' '.join(command)!r} failed with exit code {returncode}: {stderr}"
        )


class UnitFileValidationError(SystemdClientError):
    """Raised when a unit file builder fails validation."""

    def __init__(self, builder_name: str, errors: list[str]) -> None:
        self.builder_name = builder_name
        self.errors = errors
        formatted = "; ".join(errors)
        super().__init__(f"Validation failed for '{builder_name}': {formatted}")


class UnitFileInstallError(SystemdClientError):
    """Raised when installing/uninstalling a unit file fails."""

    def __init__(self, unit_name: str, operation: str, detail: str) -> None:
        self.unit_name = unit_name
        self.operation = operation
        self.detail = detail
        super().__init__(f"Failed to {operation} unit file '{unit_name}': {detail}")


class JournalError(SystemdClientError):
    """Base exception for journal-related errors."""


class JournalParseError(JournalError):
    """Raised when journal output cannot be parsed."""

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(f"Failed to parse journal output: {detail}" if detail else
                         "Failed to parse journal output")

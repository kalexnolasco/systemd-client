"""Shared validation helpers for unit file builders."""

from __future__ import annotations


def validate_absolute_path(value: str, field_name: str) -> str | None:
    """Return error message if path is not absolute, or None if valid."""
    if not value.startswith("/") and not value.startswith("-/"):
        return f"{field_name}: path must be absolute, got '{value}'"
    return None


def validate_not_empty(value: str, field_name: str) -> str | None:
    """Return error message if value is empty, or None if valid."""
    if not value.strip():
        return f"{field_name}: must not be empty"
    return None

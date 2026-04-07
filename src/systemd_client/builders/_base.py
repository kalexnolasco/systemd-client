"""Abstract base builder for systemd unit files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from systemd_client.enums import UnitType  # noqa: TC001
from systemd_client.exceptions import UnitFileValidationError
from systemd_client.models import UnitFile


class _BaseBuilder(ABC):
    """Base builder with shared [Unit] and [Install] section logic."""

    def __init__(self, name: str, unit_type: UnitType, *, template: bool = False) -> None:
        self._name = name
        self._unit_type = unit_type
        self._template = template
        self._unit_section: dict[str, list[str]] = {}
        self._install_section: dict[str, list[str]] = {}
        self._type_section: dict[str, list[str]] = {}

    # ── [Unit] section ──────────────────────────────────────────

    def description(self, text: str) -> Self:
        self._set(self._unit_section, "Description", text)
        return self

    def documentation(self, url: str) -> Self:
        self._append(self._unit_section, "Documentation", url)
        return self

    def after(self, *targets: str) -> Self:
        for t in targets:
            self._append(self._unit_section, "After", t)
        return self

    def before(self, *targets: str) -> Self:
        for t in targets:
            self._append(self._unit_section, "Before", t)
        return self

    def requires(self, *units: str) -> Self:
        for u in units:
            self._append(self._unit_section, "Requires", u)
        return self

    def wants(self, *units: str) -> Self:
        for u in units:
            self._append(self._unit_section, "Wants", u)
        return self

    def binds_to(self, *units: str) -> Self:
        for u in units:
            self._append(self._unit_section, "BindsTo", u)
        return self

    def part_of(self, *units: str) -> Self:
        for u in units:
            self._append(self._unit_section, "PartOf", u)
        return self

    def conflicts(self, *units: str) -> Self:
        for u in units:
            self._append(self._unit_section, "Conflicts", u)
        return self

    def condition_path_exists(self, path: str) -> Self:
        self._append(self._unit_section, "ConditionPathExists", path)
        return self

    # ── [Install] section ───────────────────────────────────────

    def wanted_by(self, *targets: str) -> Self:
        for t in targets:
            self._append(self._install_section, "WantedBy", t)
        return self

    def required_by(self, *targets: str) -> Self:
        for t in targets:
            self._append(self._install_section, "RequiredBy", t)
        return self

    def also(self, *units: str) -> Self:
        for u in units:
            self._append(self._install_section, "Also", u)
        return self

    def alias(self, name: str) -> Self:
        self._append(self._install_section, "Alias", name)
        return self

    # ── Build ───────────────────────────────────────────────────

    def build(self) -> UnitFile:
        """Validate and render the unit file."""
        self._validate()
        content = self._render()
        return UnitFile(
            name=self._file_name(),
            content=content,
            unit_type=self._unit_type,
        )

    @abstractmethod
    def _validate(self) -> None:
        """Validate required fields. Raises UnitFileValidationError."""
        ...

    def _raise_validation(self, errors: list[str]) -> None:
        if errors:
            raise UnitFileValidationError(self._file_name(), errors)

    # ── Rendering ───────────────────────────────────────────────

    def _file_name(self) -> str:
        suffix = self._unit_type.value
        if self._template:
            return f"{self._name}@.{suffix}"
        return f"{self._name}.{suffix}"

    def _render(self) -> str:
        sections: list[str] = []

        unit_text = self._render_section("Unit", self._unit_section)
        if unit_text:
            sections.append(unit_text)

        type_name = self._unit_type.value.capitalize()
        type_text = self._render_section(type_name, self._type_section)
        if type_text:
            sections.append(type_text)

        install_text = self._render_section("Install", self._install_section)
        if install_text:
            sections.append(install_text)

        return "\n\n".join(sections) + "\n"

    def _render_section(self, name: str, data: dict[str, list[str]]) -> str:
        if not data:
            return ""
        lines = [f"[{name}]"]
        for key, values in data.items():
            for val in values:
                lines.append(f"{key}={val}")
        return "\n".join(lines)

    # ── Internal helpers ────────────────────────────────────────

    def _set(self, section: dict[str, list[str]], key: str, value: str) -> None:
        """Set a single-value key (overwrites previous)."""
        section[key] = [value]

    def _append(self, section: dict[str, list[str]], key: str, value: str) -> None:
        """Append a value to a multi-value key."""
        section.setdefault(key, []).append(value)

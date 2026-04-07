"""PathBuilder for creating .path unit files."""

from __future__ import annotations

from typing import Self

from systemd_client.builders._base import _BaseBuilder
from systemd_client.builders._validation import validate_absolute_path
from systemd_client.enums import UnitType

_PATH_DIRECTIVES = frozenset({
    "PathExists", "PathExistsGlob", "PathChanged", "PathModified", "DirectoryNotEmpty",
})


class PathBuilder(_BaseBuilder):
    """Fluent builder for systemd path unit files."""

    def __init__(self, name: str, *, template: bool = False) -> None:
        super().__init__(name, UnitType.PATH, template=template)

    # ── [Path] section ──────────────────────────────────────────

    def path_exists(self, path: str) -> Self:
        self._append(self._type_section, "PathExists", path)
        return self

    def path_exists_glob(self, pattern: str) -> Self:
        self._append(self._type_section, "PathExistsGlob", pattern)
        return self

    def path_changed(self, path: str) -> Self:
        self._append(self._type_section, "PathChanged", path)
        return self

    def path_modified(self, path: str) -> Self:
        self._append(self._type_section, "PathModified", path)
        return self

    def directory_not_empty(self, path: str) -> Self:
        self._append(self._type_section, "DirectoryNotEmpty", path)
        return self

    def unit(self, name: str) -> Self:
        self._set(self._type_section, "Unit", name)
        return self

    def make_directory(self, val: bool) -> Self:
        self._set(self._type_section, "MakeDirectory", "true" if val else "false")
        return self

    def trigger_limit_interval_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "TriggerLimitIntervalSec", str(seconds))
        return self

    def trigger_limit_burst(self, n: int) -> Self:
        self._set(self._type_section, "TriggerLimitBurst", str(n))
        return self

    # ── Validation ──────────────────────────────────────────────

    def _validate(self) -> None:
        errors: list[str] = []

        has_path = any(k in self._type_section for k in _PATH_DIRECTIVES)
        if not has_path:
            errors.append(
                "At least one path directive is required "
                "(PathExists, PathChanged, PathModified, DirectoryNotEmpty)"
            )

        # Validate absolute paths
        for key in ("PathExists", "PathChanged", "PathModified", "DirectoryNotEmpty"):
            for val in self._type_section.get(key, []):
                err = validate_absolute_path(val, key)
                if err:
                    errors.append(err)

        self._raise_validation(errors)

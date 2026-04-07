"""TimerBuilder for creating .timer unit files."""

from __future__ import annotations

from typing import Self

from systemd_client.builders._base import _BaseBuilder
from systemd_client.enums import UnitType

_TIME_TRIGGERS = frozenset({
    "OnCalendar", "OnBootSec", "OnStartupSec",
    "OnUnitActiveSec", "OnUnitInactiveSec", "OnActiveSec",
})


class TimerBuilder(_BaseBuilder):
    """Fluent builder for systemd timer unit files."""

    def __init__(self, name: str, *, template: bool = False) -> None:
        super().__init__(name, UnitType.TIMER, template=template)

    # ── [Timer] section ─────────────────────────────────────────

    def on_calendar(self, spec: str) -> Self:
        self._set(self._type_section, "OnCalendar", spec)
        return self

    def on_boot_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "OnBootSec", str(seconds))
        return self

    def on_startup_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "OnStartupSec", str(seconds))
        return self

    def on_unit_active_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "OnUnitActiveSec", str(seconds))
        return self

    def on_unit_inactive_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "OnUnitInactiveSec", str(seconds))
        return self

    def on_active_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "OnActiveSec", str(seconds))
        return self

    def persistent(self, val: bool) -> Self:
        self._set(self._type_section, "Persistent", "true" if val else "false")
        return self

    def accuracy_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "AccuracySec", str(seconds))
        return self

    def randomized_delay_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "RandomizedDelaySec", str(seconds))
        return self

    def unit(self, name: str) -> Self:
        self._set(self._type_section, "Unit", name)
        return self

    # ── Validation ──────────────────────────────────────────────

    def _validate(self) -> None:
        errors: list[str] = []

        has_trigger = any(k in self._type_section for k in _TIME_TRIGGERS)
        if not has_trigger:
            errors.append(
                "At least one time trigger is required "
                "(OnCalendar, OnBootSec, OnStartupSec, etc.)"
            )

        self._raise_validation(errors)

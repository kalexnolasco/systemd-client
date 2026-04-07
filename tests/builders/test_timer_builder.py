"""Tests for TimerBuilder."""

import pytest

from systemd_client.builders import TimerBuilder
from systemd_client.enums import UnitType
from systemd_client.exceptions import UnitFileValidationError


class TestTimerBuilder:
    def test_on_calendar(self):
        unit = TimerBuilder("backup").on_calendar("daily").build()
        assert unit.name == "backup.timer"
        assert unit.unit_type == UnitType.TIMER
        assert "[Timer]" in unit.content
        assert "OnCalendar=daily" in unit.content

    def test_on_boot_sec(self):
        unit = TimerBuilder("startup").on_boot_sec(300).build()
        assert "OnBootSec=300" in unit.content

    def test_full_timer(self):
        unit = (
            TimerBuilder("backup")
            .description("Daily backup")
            .on_calendar("*-*-* 02:00:00")
            .persistent(True)
            .accuracy_sec(60)
            .randomized_delay_sec(300)
            .unit("backup.service")
            .wanted_by("timers.target")
            .build()
        )
        assert "Description=Daily backup" in unit.content
        assert "OnCalendar=*-*-* 02:00:00" in unit.content
        assert "Persistent=true" in unit.content
        assert "AccuracySec=60" in unit.content
        assert "RandomizedDelaySec=300" in unit.content
        assert "Unit=backup.service" in unit.content
        assert "WantedBy=timers.target" in unit.content

    def test_on_unit_active_sec(self):
        unit = TimerBuilder("poll").on_unit_active_sec(600).build()
        assert "OnUnitActiveSec=600" in unit.content

    def test_template(self):
        unit = TimerBuilder("task", template=True).on_calendar("hourly").build()
        assert unit.name == "task@.timer"


class TestTimerBuilderValidation:
    def test_no_trigger_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            TimerBuilder("backup").build()
        assert "time trigger" in str(exc_info.value).lower()

    def test_with_description_only_raises(self):
        with pytest.raises(UnitFileValidationError):
            TimerBuilder("backup").description("test").build()

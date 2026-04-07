"""Tests for TUI module (headless rendering, no terminal needed)."""

from __future__ import annotations

import pytest

from systemd_client.enums import ActiveState, LoadState, SubState
from systemd_client.models import UnitInfo

# Skip all TUI tests if ratatui-py is not installed
ratatui = pytest.importorskip("ratatui_py", reason="ratatui-py not installed")


@pytest.fixture
def sample_units():
    return [
        UnitInfo("app.service", "My App", LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING),
        UnitInfo("db.service", "Database", LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING),
        UnitInfo("old.service", "Old Svc", LoadState.LOADED, ActiveState.FAILED, SubState.FAILED),
    ]


@pytest.fixture
def sample_state(sample_units):
    return {
        "units": sample_units,
        "_filtered": sample_units,
        "selected": 0,
        "scope": "user",
        "message": "",
        "journal": [],
        "journal_unit": "",
        "timers": [],
        "filter": "",
        "filtering": False,
        "tab": 0,
    }


class TestTUIComponents:
    def test_state_color(self):
        from ratatui_py import Color

        from systemd_client.tui._app import _state_color
        assert _state_color("active") == Color.Green
        assert _state_color("failed") == Color.Red
        assert _state_color("inactive") == Color.DarkGray

    def test_build_unit_table(self, sample_state):
        from systemd_client.tui._app import _build_unit_table
        tbl = _build_unit_table(sample_state)
        assert tbl is not None

    def test_build_detail(self, sample_state):
        from systemd_client.tui._app import _build_detail
        panel = _build_detail(sample_state)
        assert panel is not None

    def test_build_detail_empty(self):
        from systemd_client.tui._app import _build_detail
        state = {"units": [], "_filtered": [], "selected": 0, "message": ""}
        panel = _build_detail(state)
        assert panel is not None

    def test_build_journal_empty(self):
        from systemd_client.tui._app import _build_journal
        state = {"journal": [], "journal_unit": ""}
        panel = _build_journal(state)
        assert panel is not None

    def test_build_help_footer(self):
        from systemd_client.tui._app import _build_help_footer
        bar = _build_help_footer()
        assert bar is not None

    def test_build_header(self, sample_state):
        from systemd_client.tui._app import _build_header
        header = _build_header(sample_state)
        assert header is not None

    def test_build_actions(self, sample_state):
        from systemd_client.tui._app import _build_actions
        panel = _build_actions(sample_state)
        assert panel is not None

    def test_build_stats_gauge(self, sample_state):
        from systemd_client.tui._app import _build_stats_gauge
        gauge = _build_stats_gauge(sample_state)
        assert gauge is not None

    def test_build_help_screen(self):
        from systemd_client.tui._app import _build_help_screen
        screen = _build_help_screen()
        assert screen is not None

    def test_build_tabs(self, sample_state):
        from systemd_client.tui._app import _build_tabs
        tabs = _build_tabs(sample_state)
        assert tabs is not None

    def test_headless_table_render(self, sample_state):
        """Test that the unit table renders correctly headlessly."""
        from ratatui_py import headless_render_table

        from systemd_client.tui._app import _build_unit_table
        tbl = _build_unit_table(sample_state)
        output = headless_render_table(120, 10, tbl)
        assert "app.service" in output
        assert "db.service" in output
        assert "old.service" in output

    def test_filter(self, sample_state):
        from systemd_client.tui._app import _build_unit_table
        sample_state["filter"] = "app"
        _build_unit_table(sample_state)
        assert len(sample_state["_filtered"]) == 1
        assert sample_state["_filtered"][0].name == "app.service"

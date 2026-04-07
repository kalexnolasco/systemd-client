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


class TestTUIComponents:
    def test_state_color(self):
        from ratatui_py import Color

        from systemd_client.tui._app import _state_color
        assert _state_color("active") == Color.Green
        assert _state_color("failed") == Color.Red
        assert _state_color("inactive") == Color.DarkGray

    def test_build_unit_table(self, sample_units):
        from systemd_client.tui._app import _build_unit_table
        state = {"units": sample_units, "selected": 0}
        tbl = _build_unit_table(state)
        # Should not raise
        assert tbl is not None

    def test_build_detail_panel(self, sample_units):
        from systemd_client.tui._app import _build_detail_panel
        state = {"units": sample_units, "selected": 0, "message": ""}
        panel = _build_detail_panel(state)
        assert panel is not None

    def test_build_detail_panel_empty(self):
        from systemd_client.tui._app import _build_detail_panel
        state = {"units": [], "selected": 0, "message": ""}
        panel = _build_detail_panel(state)
        assert panel is not None

    def test_build_journal_panel_empty(self):
        from systemd_client.tui._app import _build_journal_panel
        state = {"journal": []}
        panel = _build_journal_panel(state)
        assert panel is not None

    def test_build_help_bar(self):
        from systemd_client.tui._app import _build_help_bar
        bar = _build_help_bar()
        assert bar is not None

    def test_build_header(self, sample_units):
        from systemd_client.tui._app import _build_header
        state = {"units": sample_units, "scope": "user"}
        header = _build_header(state)
        assert header is not None

    def test_headless_render(self, sample_units):
        """Test that the full dashboard renders headlessly without errors."""
        from ratatui_py import DrawCmd, Rect, headless_render_frame

        from systemd_client.tui._app import (
            _build_detail_panel,
            _build_header,
            _build_help_bar,
            _build_journal_panel,
            _build_unit_table,
        )

        state = {
            "units": sample_units,
            "selected": 1,
            "scope": "user",
            "message": "OK: Test",
            "journal": [],
        }

        tbl = _build_unit_table(state)
        detail = _build_detail_panel(state)
        journal = _build_journal_panel(state)
        header = _build_header(state)
        footer = _build_help_bar()

        # Render just the table headlessly at 120x20 for enough room
        from ratatui_py import headless_render_table
        table_output = headless_render_table(120, 10, tbl)
        assert "app.service" in table_output
        assert "db.service" in table_output
        assert "old.service" in table_output

        # Render full frame (smoke test — no assert on content, just no crash)
        output = headless_render_frame(120, 30, [
            DrawCmd.paragraph(header, Rect(0, 0, 120, 1)),
            DrawCmd.table(tbl, Rect(0, 1, 70, 20)),
            DrawCmd.paragraph(detail, Rect(70, 1, 50, 8)),
            DrawCmd.paragraph(journal, Rect(70, 9, 50, 12)),
            DrawCmd.paragraph(footer, Rect(0, 29, 120, 1)),
        ])
        assert len(output) > 0

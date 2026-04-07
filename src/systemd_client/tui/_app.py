"""systemd-client TUI — interactive dashboard powered by ratatui-py."""

from __future__ import annotations

import sys
from typing import Any


def _fix_ratatui_so() -> None:
    """Work around ratatui-py packaging bug: .so shipped as .so.bak."""
    try:
        import importlib.util
        import shutil
        from pathlib import Path

        spec = importlib.util.find_spec("ratatui_py")
        if spec is None or spec.origin is None:
            return
        bundled = Path(spec.origin).parent / "_bundled"
        so_bak = bundled / "libratatui_ffi.so.bak"
        so_real = bundled / "libratatui_ffi.so"
        if so_bak.exists() and not so_real.exists():
            shutil.copy2(so_bak, so_real)
    except Exception:
        pass


_fix_ratatui_so()

try:
    from ratatui_py import (
        App,
        Color,
        KeyCode,
        Paragraph,
        Style,
        Table,
        Terminal,
    )
    from ratatui_py.layout import margin_rect, split_h_rect, split_v_rect
except ImportError as _exc:
    raise ImportError(
        "ratatui-py is required for the TUI. "
        "Install with: pip install systemd-client[tui]"
    ) from _exc

from systemd_client.client import SystemdClient  # noqa: E402
from systemd_client.enums import BackendType, SystemdScope  # noqa: E402


def _state_color(state: str) -> Color:
    """Map systemd active state to a color."""
    if state == "active":
        return Color.Green
    if state == "failed":
        return Color.Red
    if state in ("inactive", "dead"):
        return Color.DarkGray
    if state in ("activating", "deactivating", "reloading"):
        return Color.Yellow
    return Color.White


def _build_unit_table(state: dict[str, Any]) -> Table:
    """Build the main units table."""
    tbl = Table()
    tbl.set_headers_spans([
        [("UNIT", Style(fg=Color.Yellow).bold())],
        [("LOAD", Style(fg=Color.Yellow).bold())],
        [("ACTIVE", Style(fg=Color.Yellow).bold())],
        [("SUB", Style(fg=Color.Yellow).bold())],
        [("DESCRIPTION", Style(fg=Color.Yellow).bold())],
    ])
    tbl.set_widths_percentages([30, 10, 10, 10, 40])
    tbl.set_row_highlight_style(Style(bg=Color.Blue, fg=Color.White).bold())
    tbl.set_highlight_symbol(" > ")
    tbl.set_column_spacing(1)

    for u in state["units"]:
        color = _state_color(u.active_state.value)
        tbl.append_row_spans([
            [(u.name, Style(fg=Color.White))],
            [(u.load_state.value, Style(fg=Color.White))],
            [(u.active_state.value, Style(fg=color).bold())],
            [(u.sub_state.value, Style(fg=color))],
            [(u.description[:40], Style(fg=Color.DarkGray))],
        ])

    tbl.set_selected(state["selected"])
    tbl.set_block_title(" Units ", True)
    return tbl


def _build_detail_panel(state: dict[str, Any]) -> Paragraph:
    """Build the detail/status panel for selected unit."""
    p = Paragraph.new_empty()
    units = state["units"]
    if not units:
        p.append_span("No units loaded", Style(fg=Color.DarkGray))
        p.set_block_title(" Detail ", True)
        return p

    idx = state["selected"]
    if idx >= len(units):
        idx = 0
    u = units[idx]

    p.append_span(u.name, Style(fg=Color.Cyan).bold())
    p.line_break()
    p.append_span("  State: ", Style(fg=Color.White))
    p.append_span(
        f"{u.active_state.value} ({u.sub_state.value})",
        Style(fg=_state_color(u.active_state.value)).bold(),
    )
    p.line_break()
    p.append_span(f"  Load:  {u.load_state.value}", Style(fg=Color.White))
    p.line_break()
    p.line_break()
    p.append_span("  [s]tart [S]top [r]estart [e]nable [d]isable", Style(fg=Color.DarkGray))
    p.line_break()
    p.append_span("  [j]ournal [R]eload-daemon [q]uit", Style(fg=Color.DarkGray))

    if state.get("message"):
        p.line_break()
        p.line_break()
        msg_color = Color.Green if "OK" in state["message"] else Color.Yellow
        p.append_span(f"  {state['message']}", Style(fg=msg_color).bold())

    p.set_block_title(" Detail ", True)
    return p


def _build_journal_panel(state: dict[str, Any]) -> Paragraph:
    """Build the journal log panel."""
    p = Paragraph.new_empty()
    for entry in state.get("journal", [])[-15:]:
        ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "        "
        prio_color = Color.Red if entry.priority.value <= "3" else (
            Color.Yellow if entry.priority.value == "4" else Color.White
        )
        p.append_span(f"{ts} ", Style(fg=Color.DarkGray))
        p.append_span(entry.message[:80], Style(fg=prio_color))
        p.line_break()
    if not state.get("journal"):
        p.append_span("  Press [j] on a unit to load journal", Style(fg=Color.DarkGray))
    p.set_block_title(" Journal ", True)
    return p


def _build_help_bar() -> Paragraph:
    """Build the bottom help bar."""
    p = Paragraph.new_empty()
    keys = [
        (" q ", "Quit"), (" s ", "Start"), (" S ", "Stop"), (" r ", "Restart"),
        (" e ", "Enable"), (" d ", "Disable"), (" j ", "Journal"),
        (" / ", "Filter"), (" Tab ", "Scope"),
    ]
    for key, desc in keys:
        p.append_span(key, Style(fg=Color.Black, bg=Color.Cyan).bold())
        p.append_span(f" {desc} ", Style(fg=Color.White))
    return p


def _build_header(state: dict[str, Any]) -> Paragraph:
    """Build the top header bar."""
    p = Paragraph.new_empty()
    p.append_span(" systemd-client ", Style(fg=Color.Black, bg=Color.Green).bold())
    scope = state.get("scope", "user")
    p.append_span(f"  scope: {scope} ", Style(fg=Color.Cyan))
    count = len(state.get("units", []))
    active = sum(1 for u in state.get("units", []) if u.active_state.value == "active")
    failed = sum(1 for u in state.get("units", []) if u.active_state.value == "failed")
    p.append_span(f"  {count} units ", Style(fg=Color.White))
    if active:
        p.append_span(f" {active} active ", Style(fg=Color.Green))
    if failed:
        p.append_span(f" {failed} failed ", Style(fg=Color.Red).bold())
    return p


def render(term: Terminal, state: dict[str, Any]) -> None:
    """Main render function."""
    w, h = term.size()
    from ratatui_py import Rect
    area = Rect(0, 0, w, h)
    body = margin_rect(area, all=0)

    # Layout: header(1) | body | footer(1)
    header_area, main_area, footer_area = split_h_rect(body, 0.03, 0.92, 0.05)

    # Main: left table (60%) | right panels (40%)
    left, right = split_v_rect(main_area, 0.6, 0.4, gap=0)

    # Right: detail (40%) | journal (60%)
    detail_area, journal_area = split_h_rect(right, 0.4, 0.6)

    tbl = _build_unit_table(state)
    detail = _build_detail_panel(state)
    journal = _build_journal_panel(state)
    header = _build_header(state)
    footer = _build_help_bar()

    with term.frame() as f:
        f.paragraph(header, header_area)
        f.table(tbl, left)
        f.paragraph(detail, detail_area)
        f.paragraph(journal, journal_area)
        f.paragraph(footer, footer_area)


def on_event(term: Terminal, evt: dict[str, Any], state: dict[str, Any]) -> bool:
    """Handle keyboard events."""
    if evt.get("kind") != "key":
        return True

    ch = evt.get("ch", 0)
    code = evt.get("code", 0)
    char = chr(ch) if ch else ""
    units = state["units"]
    client: SystemdClient = state["client"]

    if char == "q" or code == KeyCode.Esc:
        return False

    if code == KeyCode.Up or char == "k":
        state["selected"] = max(0, state["selected"] - 1)
    elif code == KeyCode.Down or char == "K":
        state["selected"] = min(len(units) - 1, state["selected"] + 1)
    elif code == KeyCode.PageUp:
        state["selected"] = max(0, state["selected"] - 10)
    elif code == KeyCode.PageDown:
        state["selected"] = min(len(units) - 1, state["selected"] + 10)
    elif code == KeyCode.Home:
        state["selected"] = 0
    elif code == KeyCode.End:
        state["selected"] = len(units) - 1

    elif char and units:
        idx = state["selected"]
        if idx >= len(units):
            return True
        unit_name = units[idx].name

        try:
            if char == "s":
                client.start(unit_name)
                state["message"] = f"OK: Started {unit_name}"
            elif char == "S":
                client.stop(unit_name)
                state["message"] = f"OK: Stopped {unit_name}"
            elif char == "r":
                client.restart(unit_name)
                state["message"] = f"OK: Restarted {unit_name}"
            elif char == "e":
                client.enable(unit_name)
                state["message"] = f"OK: Enabled {unit_name}"
            elif char == "d":
                client.disable(unit_name)
                state["message"] = f"OK: Disabled {unit_name}"
            elif char == "R":
                client.daemon_reload()
                state["message"] = "OK: Daemon reloaded"
            elif char == "j":
                entries = client.journal(unit=unit_name, lines=50)
                state["journal"] = entries
                state["message"] = f"Loaded {len(entries)} journal entries"
            elif char == "\t":
                # Toggle scope
                if state["scope"] == "user":
                    state["scope"] = "system"
                else:
                    state["scope"] = "user"
                state["message"] = f"Switched to {state['scope']} scope"
                state["needs_reload"] = True
        except Exception as exc:
            state["message"] = f"Error: {exc}"

    return True


def on_tick(term: Terminal, state: dict[str, Any]) -> None:
    """Periodic refresh."""
    state["tick_count"] = state.get("tick_count", 0) + 1
    # Refresh every 4 ticks (~2 seconds at 500ms tick)
    if state["tick_count"] % 4 == 0 or state.get("needs_reload"):
        state["needs_reload"] = False
        try:
            client: SystemdClient = state["client"]
            state["units"] = client.list_units()
            if state["selected"] >= len(state["units"]):
                state["selected"] = max(0, len(state["units"]) - 1)
        except Exception:
            pass


def run_tui(
    backend: BackendType = BackendType.AUTO,
    scope: SystemdScope = SystemdScope.USER,
) -> int:
    """Launch the interactive TUI."""
    client = SystemdClient(backend=backend, scope=scope)

    try:
        units = client.list_units()
    except Exception as exc:
        print(f"Error loading units: {exc}", file=sys.stderr)
        return 1

    state: dict[str, Any] = {
        "client": client,
        "units": units,
        "selected": 0,
        "scope": scope.value,
        "message": "",
        "journal": [],
        "needs_reload": False,
        "tick_count": 0,
    }

    try:
        App(render=render, on_event=on_event, on_tick=on_tick, tick_ms=500).run(state)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()

    return 0

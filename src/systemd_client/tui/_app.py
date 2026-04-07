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
        Gauge,
        KeyCode,
        Paragraph,
        Rect,
        Style,
        Table,
        Tabs,
        Terminal,
    )
    from ratatui_py.wrappers import TableState
except ImportError as _exc:
    raise ImportError(
        "ratatui-py is required for the TUI. "
        "Install with: pip install systemd-client[tui]"
    ) from _exc

from systemd_client.client import SystemdClient  # noqa: E402
from systemd_client.enums import BackendType, SystemdScope  # noqa: E402

# ── Color theme ─────────────────────────────────────────────────

THEME = {
    "header_bg": Color.Blue,
    "header_fg": Color.White,
    "active": Color.Green,
    "failed": Color.Red,
    "inactive": Color.DarkGray,
    "loading": Color.Yellow,
    "accent": Color.Cyan,
    "muted": Color.DarkGray,
    "text": Color.White,
    "key_bg": Color.Cyan,
    "key_fg": Color.Black,
    "border": Color.Blue,
    "selected_bg": Color.Blue,
    "selected_fg": Color.White,
    "warn": Color.Yellow,
}

TAB_NAMES = [" Dashboard ", " Journal ", " Timers ", " Help "]


def _state_color(state: str) -> Color:
    """Map systemd active state to a color."""
    colors = {
        "active": THEME["active"],
        "failed": THEME["failed"],
        "inactive": THEME["inactive"],
        "dead": THEME["inactive"],
        "activating": THEME["loading"],
        "deactivating": THEME["loading"],
        "reloading": THEME["loading"],
    }
    return colors.get(state, THEME["text"])


# ── Widget builders ─────────────────────────────────────────────


def _build_tabs(state: dict[str, Any]) -> Tabs:
    """Build the tab bar."""
    t = Tabs()
    t.set_titles_spans([
        [(name, Style(fg=THEME["accent"]).bold())] for name in TAB_NAMES
    ])
    t.set_selected(state.get("tab", 0))
    t.set_divider(" | ")
    t.set_styles(
        Style(fg=THEME["muted"]),       # normal
        Style(fg=THEME["text"]).bold(),  # highlight
    )
    return t


def _build_header(state: dict[str, Any]) -> Paragraph:
    """Build the top status bar."""
    p = Paragraph.new_empty()
    p.append_span(" systemd-client ", Style(fg=THEME["header_fg"], bg=THEME["header_bg"]).bold())
    p.append_span("  ", Style())

    scope = state.get("scope", "user")
    scope_color = THEME["active"] if scope == "user" else THEME["warn"]
    p.append_span(f" {scope.upper()} ", Style(fg=Color.Black, bg=scope_color).bold())
    p.append_span("  ", Style())

    units = state.get("units", [])
    total = len(units)
    active = sum(1 for u in units if u.active_state.value == "active")
    failed = sum(1 for u in units if u.active_state.value == "failed")
    inactive = total - active - failed

    p.append_span(f"{total}", Style(fg=THEME["text"]).bold())
    p.append_span(" units  ", Style(fg=THEME["muted"]))
    p.append_span(f"{active}", Style(fg=THEME["active"]).bold())
    p.append_span(" active  ", Style(fg=THEME["muted"]))
    if failed:
        p.append_span(f"{failed}", Style(fg=THEME["failed"]).bold())
        p.append_span(" failed  ", Style(fg=THEME["muted"]))
    p.append_span(f"{inactive}", Style(fg=THEME["inactive"]))
    p.append_span(" inactive", Style(fg=THEME["muted"]))
    return p


def _build_unit_table(state: dict[str, Any]) -> Table:
    """Build the main units table."""
    tbl = Table()
    tbl.set_headers_spans([
        [("UNIT", Style(fg=THEME["accent"]).bold())],
        [("LOAD", Style(fg=THEME["accent"]).bold())],
        [("ACTIVE", Style(fg=THEME["accent"]).bold())],
        [("SUB", Style(fg=THEME["accent"]).bold())],
        [("DESCRIPTION", Style(fg=THEME["accent"]).bold())],
    ])
    tbl.set_widths_percentages([30, 10, 10, 10, 40])
    tbl.set_row_highlight_style(
        Style(bg=THEME["selected_bg"], fg=THEME["selected_fg"]).bold().reversed(),
    )
    tbl.set_highlight_symbol(" >> ")
    tbl.set_column_spacing(1)

    filter_text = state.get("filter", "").lower()
    type_filter = state.get("type_filter", "")
    filtered = []
    for u in state.get("units", []):
        if filter_text and filter_text not in u.name.lower():
            continue
        if type_filter:
            if type_filter == "failed":
                if u.active_state.value != "failed":
                    continue
            elif not u.name.endswith(f".{type_filter}"):
                continue
        filtered.append(u)
        color = _state_color(u.active_state.value)
        tbl.append_row_spans([
            [(u.name, Style(fg=THEME["text"]))],
            [(u.load_state.value, Style(fg=THEME["muted"]))],
            [(u.active_state.value, Style(fg=color).bold())],
            [(u.sub_state.value, Style(fg=color))],
            [(u.description[:50], Style(fg=THEME["muted"]))],
        ])

    state["_filtered"] = filtered
    sel = state.get("selected", 0)
    if sel >= len(filtered):
        sel = max(0, len(filtered) - 1)
        state["selected"] = sel
    tbl.set_selected(sel)
    parts = []
    if type_filter:
        parts.append(type_filter)
    if filter_text:
        parts.append(f"/{filter_text}")
    filter_label = f" [{' '.join(parts)}]" if parts else ""
    tbl.set_block_title(f" Units{filter_label} ({len(filtered)}) ", True)
    return tbl


def _build_detail(state: dict[str, Any]) -> Paragraph:
    """Build the detail panel for selected unit."""
    p = Paragraph.new_empty()
    filtered = state.get("_filtered", [])
    if not filtered:
        p.append_span("  No units selected", Style(fg=THEME["muted"]))
        p.set_block_title(" Detail ", True)
        return p

    idx = min(state.get("selected", 0), len(filtered) - 1)
    u = filtered[idx]

    p.append_span(f"  {u.name}", Style(fg=THEME["accent"]).bold())
    p.line_break()
    p.line_break()

    # State with icon
    state_val = u.active_state.value
    icon = "●" if state_val == "active" else "○" if state_val == "inactive" else "✖"
    p.append_span(f"  {icon} ", Style(fg=_state_color(state_val)).bold())
    p.append_span(f"{state_val}", Style(fg=_state_color(state_val)).bold())
    p.append_span(f" ({u.sub_state.value})", Style(fg=THEME["muted"]))
    p.line_break()

    p.append_span(f"  Load:  {u.load_state.value}", Style(fg=THEME["text"]))
    p.line_break()

    if u.description:
        p.append_span(f"  Desc:  {u.description[:35]}", Style(fg=THEME["muted"]))
        p.line_break()

    # Message
    if state.get("message"):
        p.line_break()
        is_ok = state["message"].startswith("OK")
        msg_color = THEME["active"] if is_ok else THEME["warn"]
        p.append_span(f"  {state['message'][:35]}", Style(fg=msg_color).bold())

    p.set_block_title(" Detail ", True)
    return p


def _build_actions(state: dict[str, Any]) -> Paragraph:
    """Build the actions panel."""
    p = Paragraph.new_empty()
    keys = [
        ("s", "Start", THEME["active"]),
        ("S", "Stop", THEME["failed"]),
        ("r", "Restart", THEME["warn"]),
        ("e", "Enable", THEME["accent"]),
        ("d", "Disable", THEME["muted"]),
        ("R", "Reload daemon", THEME["text"]),
        ("j", "Journal", THEME["accent"]),
        ("F", "Reset failed", THEME["failed"]),
    ]
    for key, desc, color in keys:
        p.append_span(f"  [{key}]", Style(fg=color).bold())
        p.append_span(f" {desc}", Style(fg=THEME["text"]))
        p.line_break()

    p.set_block_title(" Actions ", True)
    return p


def _build_journal(state: dict[str, Any]) -> Paragraph:
    """Build the journal log panel."""
    p = Paragraph.new_empty()
    entries = state.get("journal", [])
    if not entries:
        p.append_span("  Select a unit and press [j]", Style(fg=THEME["muted"]))
        p.line_break()
        p.append_span("  to load journal entries", Style(fg=THEME["muted"]))
    else:
        for entry in entries[-20:]:
            ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "        "
            prio = entry.priority.value
            prio_color = THEME["failed"] if prio <= "3" else (
                THEME["warn"] if prio == "4" else THEME["text"]
            )
            p.append_span(f" {ts} ", Style(fg=THEME["muted"]))
            p.append_span(entry.message[:60], Style(fg=prio_color))
            p.line_break()

    jrnl_unit = state.get("journal_unit", "")
    title = f" Journal: {jrnl_unit} " if jrnl_unit else " Journal "
    p.set_block_title(title, True)
    p.set_scroll(max(0, len(entries) - 18))
    return p


def _build_stats_gauge(state: dict[str, Any]) -> Gauge:
    """Build a stats gauge showing active percentage."""
    units = state.get("units", [])
    total = len(units) or 1
    active = sum(1 for u in units if u.active_state.value == "active")
    ratio = active / total

    g = Gauge().ratio(ratio).label(f"Active: {active}/{total} ({ratio*100:.0f}%)")
    g.set_styles(
        Style(fg=THEME["text"]),    # block style
        Style(fg=THEME["text"]),    # label style
        Style(fg=THEME["active"], bg=THEME["muted"]),  # gauge bar style
    )
    g.set_block_title(" Health ", True)
    return g


def _build_help_footer(state: dict[str, Any] | None = None) -> Paragraph:
    """Build the bottom help bar."""
    p = Paragraph.new_empty()
    keys = [
        ("↑↓", "Nav"), ("Tab", "Scope"), ("/", "Search"), ("1-4", "Tabs"),
        ("F1", "All"), ("F2", "Svc"), ("F3", "Timer"), ("F4", "Socket"), ("F5", "Failed"),
        ("s", "Start"), ("S", "Stop"), ("r", "Restart"), ("j", "Log"), ("q", "Quit"),
    ]
    for key, desc in keys:
        p.append_span(f" {key} ", Style(fg=THEME["key_fg"], bg=THEME["key_bg"]).bold())
        p.append_span(f" {desc}", Style(fg=THEME["muted"]))
        p.append_span("  ", Style())
    return p


def _build_help_screen() -> Paragraph:
    """Build the full help screen."""
    p = Paragraph.new_empty()
    sections = [
        ("Navigation", [
            ("↑ / ↓", "Move selection up/down"),
            ("PgUp / PgDn", "Move 10 items up/down"),
            ("Home / End", "Jump to first/last"),
            ("Tab", "Toggle user/system scope"),
            ("1-4", "Switch between tabs"),
            ("/ + text", "Filter units by name"),
            ("Esc", "Clear filter / Exit"),
            ("q", "Quit"),
        ]),
        ("Type Filters", [
            ("F1", "Show all units"),
            ("F2", "Show only .service units"),
            ("F3", "Show only .timer units"),
            ("F4", "Show only .socket units"),
            ("F5", "Show only failed units"),
        ]),
        ("Unit Operations", [
            ("s", "Start selected unit"),
            ("S", "Stop selected unit"),
            ("r", "Restart selected unit"),
            ("e", "Enable selected unit"),
            ("d", "Disable selected unit"),
            ("F", "Reset failed state"),
            ("R", "Reload systemd daemon"),
        ]),
        ("Journal", [
            ("j", "Load journal for selected unit"),
        ]),
    ]
    for section, items in sections:
        p.line_break()
        p.append_span(f"  {section}", Style(fg=THEME["accent"]).bold())
        p.line_break()
        p.append_span("  " + "─" * 40, Style(fg=THEME["muted"]))
        p.line_break()
        for key, desc in items:
            p.append_span(f"    {key:<15}", Style(fg=THEME["warn"]).bold())
            p.append_span(desc, Style(fg=THEME["text"]))
            p.line_break()

    p.set_block_title(" Help — Keyboard Shortcuts ", True)
    return p


def _build_timers_tab(state: dict[str, Any]) -> Table:
    """Build the timers tab table."""
    tbl = Table()
    tbl.set_headers_spans([
        [("TIMER", Style(fg=THEME["accent"]).bold())],
        [("TIME LEFT", Style(fg=THEME["accent"]).bold())],
        [("ACTIVATES", Style(fg=THEME["accent"]).bold())],
    ])
    tbl.set_widths_percentages([40, 25, 35])
    tbl.set_column_spacing(1)

    for t in state.get("timers", []):
        time_left = str(t.time_left) if t.time_left is not None else "-"
        tbl.append_row_spans([
            [(str(t.name), Style(fg=THEME["text"]))],
            [(time_left, Style(fg=THEME["active"]))],
            [(str(t.activates or "-"), Style(fg=THEME["muted"]))],
        ])

    count = len(state.get("timers", []))
    tbl.set_block_title(f" Timers ({count}) ", True)
    return tbl


# ── Layout & Render ─────────────────────────────────────────────


def render(term: Terminal, state: dict[str, Any]) -> None:
    """Main render function.

    Uses individual draw calls instead of draw_frame so we can use
    draw_table_state for proper row highlight/selection.
    """
    w, h = term.size()

    # Layout: header(1) + tabs(1) + body + footer(1)
    header_h = 1
    tabs_h = 1
    footer_h = 1
    body_y = header_h + tabs_h
    body_h = h - header_h - tabs_h - footer_h

    # Draw chrome (header, tabs, footer)
    term.draw_paragraph(_build_header(state), Rect(0, 0, w, header_h))
    term.draw_tabs(_build_tabs(state), Rect(0, header_h, w, tabs_h))
    term.draw_paragraph(_build_help_footer(state), Rect(0, h - footer_h, w, footer_h))

    tab = state.get("tab", 0)

    if tab == 0:  # Dashboard
        left_w = int(w * 0.6)
        right_w = w - left_w
        left_rect = Rect(0, body_y, left_w, body_h)

        # Draw table with TableState for proper highlight
        tbl = _build_unit_table(state)
        ts = TableState()
        ts.set_selected(state.get("selected", 0))
        term.draw_table_state(tbl, ts, left_rect)

        # Right panels
        detail_h = int(body_h * 0.4)
        actions_h = int(body_h * 0.4)
        gauge_h = max(3, body_h - detail_h - actions_h)
        actions_h = body_h - detail_h - gauge_h  # recalc

        term.draw_paragraph(
            _build_detail(state), Rect(left_w, body_y, right_w, detail_h),
        )
        term.draw_paragraph(
            _build_actions(state), Rect(left_w, body_y + detail_h, right_w, actions_h),
        )
        term.draw_gauge(
            _build_stats_gauge(state),
            Rect(left_w, body_y + detail_h + actions_h, right_w, gauge_h),
        )

    elif tab == 1:  # Journal
        term.draw_paragraph(_build_journal(state), Rect(0, body_y, w, body_h))

    elif tab == 2:  # Timers
        tbl = _build_timers_tab(state)
        term.draw_table(tbl, Rect(0, body_y, w, body_h))

    elif tab == 3:  # Help
        term.draw_paragraph(_build_help_screen(), Rect(0, body_y, w, body_h))


# ── Event Handling ──────────────────────────────────────────────


def on_event(term: Terminal, evt: dict[str, Any], state: dict[str, Any]) -> bool:
    """Handle keyboard events."""
    if evt.get("kind") != "key":
        return True

    ch = evt.get("ch", 0)
    code = evt.get("code", 0)
    char = chr(ch) if ch else ""
    units = state.get("_filtered", state.get("units", []))
    client: SystemdClient = state["client"]

    # Filter mode
    if state.get("filtering"):
        if code == KeyCode.Esc:
            state["filtering"] = False
            state["filter"] = ""
        elif code == KeyCode.Enter:
            state["filtering"] = False
        elif code == KeyCode.Backspace:
            state["filter"] = state.get("filter", "")[:-1]
        elif char and char.isprintable():
            state["filter"] = state.get("filter", "") + char
        return True

    # Quit
    if char == "q" or (code == KeyCode.Esc and not state.get("filter")):
        return False

    # Clear filters on Esc
    if code == KeyCode.Esc:
        state["filter"] = ""
        state["type_filter"] = ""
        return True

    # Tab switching (1-4 keys)
    if char in ("1", "2", "3", "4"):
        new_tab = int(char) - 1
        state["tab"] = new_tab
        if new_tab == 2 and not state.get("timers"):
            import contextlib
            with contextlib.suppress(Exception):
                state["timers"] = client.list_timers()
        return True

    # Type filters (F1-F5)
    type_filter_map = {
        KeyCode.F1: "",
        KeyCode.F2: "service",
        KeyCode.F3: "timer",
        KeyCode.F4: "socket",
        KeyCode.F5: "failed",
    }
    if code in type_filter_map:
        state["type_filter"] = type_filter_map[code]
        state["selected"] = 0
        label = type_filter_map[code] or "all"
        state["message"] = f"Filter: {label}"
        return True

    # Tab key = scope toggle
    if code == KeyCode.Tab:
        if state["scope"] == "user":
            state["scope"] = "system"
        else:
            state["scope"] = "user"
        state["message"] = f"Scope: {state['scope']}"
        state["needs_reload"] = True
        client.close()
        state["client"] = SystemdClient(scope=SystemdScope(state["scope"]))
        return True

    # Filter mode entry
    if char == "/":
        state["filtering"] = True
        state["filter"] = ""
        return True

    # Navigation
    if code == KeyCode.Up:
        state["selected"] = max(0, state["selected"] - 1)
    elif code == KeyCode.Down:
        state["selected"] = min(len(units) - 1, state["selected"] + 1)
    elif code == KeyCode.PageUp:
        state["selected"] = max(0, state["selected"] - 10)
    elif code == KeyCode.PageDown:
        state["selected"] = min(len(units) - 1, state["selected"] + 10)
    elif code == KeyCode.Home:
        state["selected"] = 0
    elif code == KeyCode.End:
        state["selected"] = max(0, len(units) - 1)

    # Unit operations (work from dashboard tab)
    elif char and units and state.get("tab", 0) in (0, 1):
        idx = min(state.get("selected", 0), len(units) - 1)
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
            elif char == "F":
                client.reset_failed(unit_name)
                state["message"] = f"OK: Reset failed {unit_name}"
            elif char == "j":
                entries = client.journal(unit=unit_name, lines=100)
                state["journal"] = entries
                state["journal_unit"] = unit_name
                state["tab"] = 1  # switch to journal tab
                state["message"] = f"Loaded {len(entries)} entries"
        except Exception as exc:
            state["message"] = f"Error: {exc}"

    return True


def on_tick(term: Terminal, state: dict[str, Any]) -> None:
    """Periodic refresh."""
    state["tick_count"] = state.get("tick_count", 0) + 1
    if state["tick_count"] % 4 == 0 or state.get("needs_reload"):
        state["needs_reload"] = False
        try:
            client: SystemdClient = state["client"]
            state["units"] = client.list_units()
            if state["selected"] >= len(state["units"]):
                state["selected"] = max(0, len(state["units"]) - 1)
        except Exception:
            pass


# ── Entry point ─────────────────────────────────────────────────


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
        "journal_unit": "",
        "timers": [],
        "filter": "",
        "type_filter": "",
        "filtering": False,
        "tab": 0,
        "needs_reload": False,
        "tick_count": 0,
        "_filtered": units,
    }

    try:
        App(render=render, on_event=on_event, on_tick=on_tick, tick_ms=500).run(state)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()

    return 0

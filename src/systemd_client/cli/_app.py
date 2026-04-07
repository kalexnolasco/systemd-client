"""CLI entry point using argparse."""

from __future__ import annotations

import argparse
import sys

from systemd_client._version import __version__
from systemd_client.cli._formatters import (
    format_journal_json,
    format_journal_table,
    format_status_json,
    format_status_table,
    format_unit_files_json,
    format_unit_files_table,
    format_units_json,
    format_units_table,
)
from systemd_client.client import SystemdClient
from systemd_client.enums import BackendType, JournalPriority, SystemdScope
from systemd_client.exceptions import SystemdClientError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="systemd-client",
        description="High-level CLI for systemd services",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--backend", choices=["auto", "subprocess", "dbus"],
        default="auto", help="Backend to use (default: auto)",
    )
    parser.add_argument(
        "--scope", choices=["user", "system"],
        default="user", help="Scope: user session or system-wide (default: user)",
    )
    parser.add_argument("--json", dest="use_json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List units")
    p_list.add_argument("--type", dest="unit_type", help="Filter by unit type")
    p_list.add_argument("--state", help="Filter by active state")

    # list-unit-files
    p_files = sub.add_parser("list-unit-files", help="List installed unit files")
    p_files.add_argument("--type", dest="unit_type", help="Filter by unit type")
    p_files.add_argument("--state", help="Filter by unit file state")

    # status
    p_status = sub.add_parser("status", help="Show unit status")
    p_status.add_argument("unit", help="Unit name")

    # cat
    p_cat = sub.add_parser("cat", help="Show unit file content")
    p_cat.add_argument("unit", help="Unit name")

    # start/stop/restart/reload/try-restart/reload-or-restart
    for cmd in ("start", "stop", "restart", "reload", "try-restart", "reload-or-restart"):
        p = sub.add_parser(cmd, help=f"{cmd.capitalize()} a unit")
        p.add_argument("unit", nargs="+", help="Unit name(s)")
        p.add_argument("--no-block", action="store_true", help="Do not wait for completion")

    # enable/disable/mask/unmask
    for cmd in ("enable", "disable", "mask", "unmask"):
        p = sub.add_parser(cmd, help=f"{cmd.capitalize()} a unit")
        p.add_argument("unit", help="Unit name")

    # daemon-reload
    sub.add_parser("daemon-reload", help="Reload systemd daemon")

    # reset-failed
    p_reset = sub.add_parser("reset-failed", help="Reset failed state")
    p_reset.add_argument("unit", nargs="?", help="Unit name (all if omitted)")

    # journal
    p_journal = sub.add_parser("journal", help="Query journal entries")
    p_journal.add_argument("--unit", "-u", help="Filter by unit name")
    p_journal.add_argument(
        "--lines", "-n", type=int, default=25, help="Number of lines (default: 25)",
    )
    p_journal.add_argument("--since", help="Show entries since (e.g. '1h ago', '2024-01-01')")
    p_journal.add_argument("--until", help="Show entries until")
    p_journal.add_argument(
        "--priority", "-p", choices=[p.name.lower() for p in JournalPriority],
        help="Minimum priority level",
    )
    p_journal.add_argument("--grep", "-g", help="Filter by regex pattern")
    p_journal.add_argument("--follow", "-f", action="store_true", help="Follow new entries")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        client = SystemdClient(
            backend=BackendType(args.backend),
            scope=SystemdScope(args.scope),
        )
    except SystemdClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        with client:
            return _dispatch(client, args)
    except SystemdClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def _dispatch(client: SystemdClient, args: argparse.Namespace) -> int:
    cmd = args.command

    if cmd == "list":
        units = client.list_units(unit_type=args.unit_type, state=args.state)
        if args.use_json:
            print(format_units_json(units))
        else:
            print(format_units_table(units, no_color=args.no_color))

    elif cmd == "list-unit-files":
        files = client.list_unit_files(unit_type=args.unit_type, state=args.state)
        if args.use_json:
            print(format_unit_files_json(files))
        else:
            print(format_unit_files_table(files, no_color=args.no_color))

    elif cmd == "status":
        status = client.status(args.unit)
        if args.use_json:
            print(format_status_json(status))
        else:
            print(format_status_table(status, no_color=args.no_color))

    elif cmd == "cat":
        content = client.cat(args.unit)
        print(content, end="")

    elif cmd in ("start", "stop", "restart", "reload", "try-restart", "reload-or-restart"):
        # Normalize command name to method name
        method_name = cmd.replace("-", "_")
        units = args.unit  # list of unit names
        no_block = args.no_block

        if len(units) == 1:
            getattr(client, method_name)(units[0], no_block=no_block)
            print(f"{cmd.capitalize()}ed {units[0]}")
        else:
            # Batch: use batch methods for start/stop/restart
            batch_method = f"{method_name}_units"
            if hasattr(client, batch_method):
                getattr(client, batch_method)(units, no_block=no_block)
            else:
                for u in units:
                    getattr(client, method_name)(u, no_block=no_block)
            print(f"{cmd.capitalize()}ed {', '.join(units)}")

    elif cmd in ("enable", "disable", "mask", "unmask"):
        result = getattr(client, cmd)(args.unit)
        print(f"{cmd.capitalize()}d {args.unit}")
        for change in result.changes:
            print(f"  {change[0]} {change[1]} {change[2]}".rstrip())

    elif cmd == "daemon-reload":
        client.daemon_reload()
        print("Daemon reloaded")

    elif cmd == "reset-failed":
        client.reset_failed(args.unit)
        if args.unit:
            print(f"Reset failed state for {args.unit}")
        else:
            print("Reset all failed states")

    elif cmd == "journal":
        priority = JournalPriority[args.priority.upper()] if args.priority else None

        if args.follow:
            for entry in client.journal_follow(
                unit=args.unit, lines=args.lines, priority=priority,
            ):
                if args.use_json:
                    import json
                    from dataclasses import asdict
                    print(json.dumps(asdict(entry), default=str))
                else:
                    ts = entry.timestamp.strftime("%b %d %H:%M:%S") if entry.timestamp else ""
                    ident = entry.syslog_identifier or ""
                    pid_str = f"[{entry.pid}]" if entry.pid else ""
                    print(f"{ts} {ident}{pid_str}: {entry.message}")
        else:
            entries = client.journal(
                unit=args.unit, lines=args.lines, since=args.since,
                until=args.until, priority=priority, grep=args.grep,
            )
            if args.use_json:
                print(format_journal_json(entries))
            else:
                print(format_journal_table(entries, no_color=args.no_color))

    return 0

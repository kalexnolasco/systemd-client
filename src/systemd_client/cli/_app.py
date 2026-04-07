"""CLI entry point using argparse."""

from __future__ import annotations

import argparse
import json
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

    # environment
    sub.add_parser("show-environment", help="Show manager environment variables")
    p_setenv = sub.add_parser("set-environment", help="Set environment variables")
    p_setenv.add_argument("vars", nargs="+", help="Variables (KEY=VALUE)")
    p_unsetenv = sub.add_parser("unset-environment", help="Unset environment variables")
    p_unsetenv.add_argument("names", nargs="+", help="Variable names to unset")

    # sessions
    sub.add_parser("list-sessions", help="List active login sessions")
    sub.add_parser("list-users", help="List logged-in users")

    # power management
    sub.add_parser("poweroff", help="Power off the system")
    sub.add_parser("reboot", help="Reboot the system")
    sub.add_parser("suspend", help="Suspend the system")
    sub.add_parser("hibernate", help="Hibernate the system")

    # analyze
    sub.add_parser("analyze-blame", help="Show slowest units at boot")
    p_asec = sub.add_parser("analyze-security", help="Analyze unit security hardening")
    p_asec.add_argument("unit", help="Unit name")
    p_averify = sub.add_parser("analyze-verify", help="Verify unit file syntax")
    p_averify.add_argument("unit", help="Unit name")

    # list-timers / list-sockets
    sub.add_parser("list-timers", help="List active timers")
    sub.add_parser("list-sockets", help="List active sockets")

    # resources
    p_res = sub.add_parser("resources", help="Show resource usage of a unit")
    p_res.add_argument("unit", help="Unit name")

    # kill
    p_kill = sub.add_parser("kill", help="Send signal to a unit")
    p_kill.add_argument("unit", help="Unit name")
    p_kill.add_argument("--signal", "-s", default="SIGTERM", help="Signal (default: SIGTERM)")

    # dependencies
    p_deps = sub.add_parser("list-dependencies", help="Show unit dependency tree")
    p_deps.add_argument("unit", help="Unit name")

    # run (transient)
    p_run = sub.add_parser("run", help="Run a command as a transient systemd service")
    p_run.add_argument("cmd", nargs="+", help="Command to run")
    p_run.add_argument("--name", help="Unit name for the transient service")
    p_run.add_argument("--wait", action="store_true", help="Wait for completion")
    p_run.add_argument(
        "--property", dest="properties", nargs="*", help="Properties (KEY=VALUE)",
    )
    p_run.add_argument("--remain-after-exit", action="store_true", help="Keep unit after exit")
    p_run.add_argument("--on-calendar", help="Schedule as timer (e.g. daily, hourly)")

    # create-service
    p_cs = sub.add_parser("create-service", help="Generate a .service unit file")
    p_cs.add_argument("--name", required=True, help="Service name (without .service)")
    p_cs.add_argument("--exec-start", required=True, help="ExecStart command")
    p_cs.add_argument("--description", help="Unit description")
    p_cs.add_argument("--type", dest="svc_type", default="simple", help="Service type")
    p_cs.add_argument("--user", help="Run as user")
    p_cs.add_argument("--group", help="Run as group")
    p_cs.add_argument("--working-directory", help="Working directory")
    p_cs.add_argument("--restart", default=None, help="Restart policy")
    p_cs.add_argument("--restart-sec", type=int, help="Restart delay in seconds")
    p_cs.add_argument("--after", nargs="*", help="After= dependencies")
    p_cs.add_argument("--wanted-by", default="default.target", help="Install WantedBy target")
    p_cs.add_argument("--environment", nargs="*", help="Environment vars (KEY=VALUE)")
    p_cs.add_argument("--template", action="store_true", help="Create template unit (@)")
    p_cs.add_argument(
        "--install", dest="do_install", action="store_true", help="Install after creating",
    )

    # create-timer
    p_ct = sub.add_parser("create-timer", help="Generate a .timer unit file")
    p_ct.add_argument("--name", required=True, help="Timer name (without .timer)")
    p_ct.add_argument("--on-calendar", help="OnCalendar spec (e.g. daily, *-*-* 02:00)")
    p_ct.add_argument("--on-boot-sec", type=int, help="OnBootSec in seconds")
    p_ct.add_argument("--unit", dest="timer_unit", help="Service unit to trigger")
    p_ct.add_argument("--persistent", action="store_true", help="Persistent timer")
    p_ct.add_argument("--description", help="Unit description")
    p_ct.add_argument("--wanted-by", default="timers.target", help="Install WantedBy target")
    p_ct.add_argument(
        "--install", dest="do_install", action="store_true", help="Install after creating",
    )

    # install (from file)
    p_inst = sub.add_parser("install", help="Install a unit file")
    p_inst.add_argument("unit", help="Unit name")
    p_inst.add_argument("--from-file", required=True, help="Path to unit file")

    # uninstall
    p_uninst = sub.add_parser("uninstall", help="Remove an installed unit file")
    p_uninst.add_argument("unit", help="Unit name")

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

    elif cmd == "show-environment":
        env = client.show_environment()
        if args.use_json:
            print(json.dumps(env, indent=2))
        else:
            for k, v in sorted(env.items()):
                print(f"{k}={v}")

    elif cmd == "set-environment":
        variables = dict(kv.split("=", 1) for kv in args.vars)
        client.set_environment(variables)
        print(f"Set {len(variables)} variable(s)")

    elif cmd == "unset-environment":
        client.unset_environment(args.names)
        print(f"Unset {len(args.names)} variable(s)")

    elif cmd == "list-sessions":
        sessions = client.list_sessions()
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps([asdict(s) for s in sessions], indent=2))
        elif not sessions:
            print("No sessions found.")
        else:
            for s in sessions:
                print(f"  {s.id}  {s.user} (uid={s.uid})  {s.tty}  {s.state}")

    elif cmd == "list-users":
        users = client.list_users()
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps([asdict(u) for u in users], indent=2))
        elif not users:
            print("No users found.")
        else:
            for u in users:
                print(f"  {u.uid}  {u.name}  {u.state}")

    elif cmd in ("poweroff", "reboot", "suspend", "hibernate"):
        getattr(client, cmd)()
        print(f"{cmd.capitalize()} initiated")

    elif cmd == "analyze-blame":
        entries = client.analyze_blame()
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps([asdict(e) for e in entries], indent=2))
        else:
            for e in entries:
                secs = e.time_us / 1_000_000
                print(f"  {secs:>8.3f}s  {e.unit}")

    elif cmd == "analyze-security":
        analysis = client.analyze_security(args.unit)
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps(asdict(analysis), indent=2))
        else:
            score = analysis.exposure
            color = "\033[32m" if score < 3 else "\033[33m" if score < 7 else "\033[31m"
            reset = "\033[0m" if not args.no_color else ""
            color = color if not args.no_color else ""
            print(f"  {args.unit}: {color}{score:.1f}/10.0 exposure{reset}")
            for issue in analysis.issues[:20]:
                print(f"    [{issue.severity}] {issue.description}: {issue.value}")

    elif cmd == "analyze-verify":
        messages = client.analyze_verify(args.unit)
        if not messages:
            print(f"{args.unit}: OK")
        else:
            for msg in messages:
                print(f"  {msg}")

    elif cmd == "list-timers":
        timers = client.list_timers()
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps([asdict(t) for t in timers], default=str, indent=2))
        elif not timers:
            print("No timers found.")
        else:
            for t in timers:
                act = f" -> {t.activates}" if t.activates else ""
                left = f" ({t.time_left})" if t.time_left else ""
                print(f"{t.name}{act}{left}")

    elif cmd == "list-sockets":
        sockets = client.list_sockets()
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps([asdict(s) for s in sockets], default=str, indent=2))
        elif not sockets:
            print("No sockets found.")
        else:
            for s in sockets:
                print(f"{s.name}  {s.listen}  {s.type}")

    elif cmd == "resources":
        usage = client.get_resource_usage(args.unit)
        if args.use_json:
            from dataclasses import asdict
            print(json.dumps(asdict(usage), default=str, indent=2))
        else:
            if usage.cpu_usage_nsec is not None:
                print(f"  CPU: {usage.cpu_usage_nsec / 1_000_000_000:.3f}s")
            if usage.memory_current is not None:
                print(f"  Memory: {usage.memory_current / 1024 / 1024:.1f}MB")
            if usage.memory_peak is not None:
                print(f"  Memory peak: {usage.memory_peak / 1024 / 1024:.1f}MB")
            if usage.tasks_current is not None:
                print(f"  Tasks: {usage.tasks_current}")
            if usage.io_read_bytes is not None:
                print(f"  IO read: {usage.io_read_bytes / 1024:.0f}KB")
            if usage.io_write_bytes is not None:
                print(f"  IO write: {usage.io_write_bytes / 1024:.0f}KB")

    elif cmd == "kill":
        client.kill(args.unit, signal=args.signal)
        print(f"Sent {args.signal} to {args.unit}")

    elif cmd == "list-dependencies":
        deps = client.list_dependencies(args.unit)
        for d in deps:
            print(f"  {d}")

    elif cmd == "run":
        props = {}
        if args.properties:
            props = dict(kv.split("=", 1) for kv in args.properties)
        if args.on_calendar:
            result = client.run_on_calendar(
                args.on_calendar, args.cmd, name=args.name,
            )
            print(f"Scheduled timer: {result.unit_name}")
        else:
            result = client.run(
                args.cmd, name=args.name, wait=args.wait,
                properties=props or None,
                remain_after_exit=args.remain_after_exit,
            )
            msg = f"Running: {result.unit_name}"
            if result.pid:
                msg += f" (PID {result.pid})"
            print(msg)

    elif cmd == "create-service":
        from systemd_client.builders import ServiceBuilder
        b = ServiceBuilder(args.name, template=args.template)
        if args.description:
            b.description(args.description)
        b.type_(args.svc_type)
        b.exec_start(args.exec_start)
        if args.user:
            b.user(args.user)
        if args.group:
            b.group(args.group)
        if args.working_directory:
            b.working_directory(args.working_directory)
        if args.restart:
            b.restart(args.restart)
        if args.restart_sec:
            b.restart_sec(args.restart_sec)
        if args.after:
            b.after(*args.after)
        if args.environment:
            env = dict(kv.split("=", 1) for kv in args.environment)
            b.environment(env)
        b.wanted_by(args.wanted_by)
        unit = b.build()
        if args.do_install:
            path = client.install(unit)
            print(f"Installed {unit.name} -> {path}")
        else:
            print(unit.content, end="")

    elif cmd == "create-timer":
        from systemd_client.builders import TimerBuilder
        b = TimerBuilder(args.name)
        if args.description:
            b.description(args.description)
        if args.on_calendar:
            b.on_calendar(args.on_calendar)
        if args.on_boot_sec:
            b.on_boot_sec(args.on_boot_sec)
        if args.timer_unit:
            b.unit(args.timer_unit)
        if args.persistent:
            b.persistent(True)
        b.wanted_by(args.wanted_by)
        unit = b.build()
        if args.do_install:
            path = client.install(unit)
            print(f"Installed {unit.name} -> {path}")
        else:
            print(unit.content, end="")

    elif cmd == "install":
        from pathlib import Path

        from systemd_client.enums import UnitType
        from systemd_client.models import UnitFile
        content = Path(args.from_file).read_text(encoding="utf-8")
        suffix = args.unit.rsplit(".", 1)[-1] if "." in args.unit else "service"
        unit_type = UnitType(suffix)
        unit = UnitFile(name=args.unit, content=content, unit_type=unit_type)
        path = client.install(unit)
        print(f"Installed {args.unit} -> {path}")

    elif cmd == "uninstall":
        client.uninstall(args.unit)
        print(f"Uninstalled {args.unit}")

    elif cmd == "journal":
        priority = JournalPriority[args.priority.upper()] if args.priority else None

        if args.follow:
            for entry in client.journal_follow(
                unit=args.unit, lines=args.lines, priority=priority,
            ):
                if args.use_json:
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

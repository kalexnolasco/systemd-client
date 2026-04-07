"""Subprocess backend: communicates with systemd via systemctl --user/--system."""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from systemd_client.backends._base import AbstractBackend
from systemd_client.backends._paths import unit_file_dir
from systemd_client.enums import (
    ActiveState,
    LoadState,
    SubState,
    SystemdScope,
    UnitFileState,
)
from systemd_client.exceptions import (
    SubprocessError,
    UnitFileInstallError,
    UnitNotFoundError,
    UnitOperationError,
)
from systemd_client.models import (
    EnableResult,
    ResourceUsage,
    SessionInfo,
    SocketInfo,
    TimerInfo,
    TransientResult,
    UnitFileInfo,
    UnitInfo,
    UnitStatus,
    UserInfo,
)

if TYPE_CHECKING:
    from systemd_client.models import UnitFile


class SubprocessBackend(AbstractBackend):
    """Backend that uses systemctl/journalctl subprocess calls."""

    def __init__(self, scope: SystemdScope = SystemdScope.USER) -> None:
        self._scope = scope

    @property
    def _scope_flag(self) -> str:
        return f"--{self._scope.value}"

    async def _run_systemctl(self, *args: str, check: bool = True) -> tuple[str, str, int]:
        """Run a systemctl command and return (stdout, stderr, returncode)."""
        cmd = ["systemctl", self._scope_flag, *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = proc.returncode or 0

        if check and returncode != 0:
            raise SubprocessError(cmd, returncode, stderr.strip())

        return stdout, stderr, returncode

    async def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        args = ["list-units", "--output=json", "--no-pager", "--all"]
        if unit_type:
            args.append(f"--type={unit_type}")
        if state:
            args.append(f"--state={state}")

        stdout, _, _ = await self._run_systemctl(*args)
        data = json.loads(stdout) if stdout.strip() else []

        units: list[UnitInfo] = []
        for entry in data:
            try:
                units.append(UnitInfo(
                    name=entry["unit"],
                    description=entry.get("description", ""),
                    load_state=LoadState(entry.get("load", "loaded")),
                    active_state=ActiveState(entry.get("active", "inactive")),
                    sub_state=SubState(entry.get("sub", "dead")),
                    unit_file_state=None,
                ))
            except ValueError:
                continue
        return units

    async def list_unit_files(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitFileInfo]:
        args = ["list-unit-files", "--output=json", "--no-pager"]
        if unit_type:
            args.append(f"--type={unit_type}")
        if state:
            args.append(f"--state={state}")

        stdout, _, _ = await self._run_systemctl(*args)
        data = json.loads(stdout) if stdout.strip() else []

        files: list[UnitFileInfo] = []
        for entry in data:
            try:
                files.append(UnitFileInfo(
                    name=entry.get("unit_file", entry.get("unit", "")),
                    state=UnitFileState(entry.get("state", "disabled")),
                    preset=entry.get("preset") or None,
                ))
            except ValueError:
                continue
        return files

    async def get_unit_status(self, unit_name: str) -> UnitStatus:
        try:
            stdout, _, _ = await self._run_systemctl("show", unit_name, "--no-pager")
        except SubprocessError as exc:
            if "not found" in exc.stderr.lower():
                raise UnitNotFoundError(unit_name) from exc
            raise

        props: dict[str, str] = {}
        for line in stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()

        if props.get("LoadState") == "not-found":
            raise UnitNotFoundError(unit_name)

        def _parse_timestamp(key: str) -> datetime | None:
            raw = props.get(key, "")
            if not raw or raw == "0" or raw.startswith("n/a"):
                return None
            # systemctl show outputs microseconds since epoch for *USec fields
            usec_key = key + "USec" if not key.endswith("USec") else key
            raw_usec = props.get(usec_key, "")
            if raw_usec and raw_usec != "0":
                try:
                    return datetime.fromtimestamp(int(raw_usec) / 1_000_000, tz=UTC)
                except (ValueError, OSError):
                    pass
            # Try to parse the human-readable timestamp
            raw_ts = props.get(key, "")
            if raw_ts and raw_ts != "n/a":
                try:
                    return datetime.fromisoformat(raw_ts)
                except ValueError:
                    pass
            return None

        def _safe_int(key: str, *, zero_is_none: bool = True) -> int | None:
            """Parse an integer property. zero_is_none=True for PIDs, False for exit codes."""
            raw = props.get(key, "")
            if not raw:
                return None
            try:
                val = int(raw)
                if zero_is_none and val == 0:
                    return None
                return val
            except ValueError:
                return None

        def _safe_enum(enum_cls: type, key: str, default: str) -> object:
            raw = props.get(key, default)
            try:
                return enum_cls(raw)
            except ValueError:
                return enum_cls(default)

        triggered_by = [
            t.strip() for t in props.get("TriggeredBy", "").split() if t.strip()
        ]
        documentation = [
            d.strip() for d in props.get("Documentation", "").split() if d.strip()
        ]

        return UnitStatus(
            name=props.get("Id", unit_name),
            description=props.get("Description", ""),
            load_state=_safe_enum(LoadState, "LoadState", "loaded"),  # type: ignore[arg-type]
            active_state=_safe_enum(ActiveState, "ActiveState", "inactive"),  # type: ignore[arg-type]
            sub_state=_safe_enum(SubState, "SubState", "dead"),  # type: ignore[arg-type]
            unit_file_state=(  # type: ignore[arg-type]
                _safe_enum(UnitFileState, "UnitFileState", "disabled")
                if props.get("UnitFileState") else None
            ),
            fragment_path=props.get("FragmentPath") or None,
            active_enter_timestamp=_parse_timestamp("ActiveEnterTimestamp"),
            active_exit_timestamp=_parse_timestamp("ActiveExitTimestamp"),
            inactive_enter_timestamp=_parse_timestamp("InactiveEnterTimestamp"),
            inactive_exit_timestamp=_parse_timestamp("InactiveExitTimestamp"),
            main_pid=_safe_int("MainPID"),
            exec_main_status=_safe_int("ExecMainStatus", zero_is_none=False),
            result=props.get("Result") or None,
            triggered_by=triggered_by,
            documentation=documentation,
            properties=props,
        )

    async def cat(self, unit_name: str) -> str:
        try:
            stdout, _, _ = await self._run_systemctl("cat", unit_name)
        except SubprocessError as exc:
            if "not found" in exc.stderr.lower() or "No files found" in exc.stderr:
                raise UnitNotFoundError(unit_name) from exc
            raise
        return stdout

    async def _unit_action(
        self, action: str, unit_name: str, no_block: bool = False,
    ) -> None:
        args = [action]
        if no_block:
            args.append("--no-block")
        args.append(unit_name)
        try:
            await self._run_systemctl(*args)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, action, exc.stderr) from exc

    async def start_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("start", unit_name, no_block)

    async def stop_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("stop", unit_name, no_block)

    async def restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("restart", unit_name, no_block)

    async def reload_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("reload", unit_name, no_block)

    async def try_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("try-restart", unit_name, no_block)

    async def reload_or_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action("reload-or-restart", unit_name, no_block)

    async def _batch_action(
        self, action: str, unit_names: list[str], no_block: bool = False,
    ) -> None:
        args = [action]
        if no_block:
            args.append("--no-block")
        args.extend(unit_names)
        try:
            await self._run_systemctl(*args)
        except SubprocessError as exc:
            raise UnitOperationError(
                ", ".join(unit_names), action, exc.stderr,
            ) from exc

    async def start_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await self._batch_action("start", unit_names, no_block)

    async def stop_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await self._batch_action("stop", unit_names, no_block)

    async def restart_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await self._batch_action("restart", unit_names, no_block)

    async def _enable_disable_op(self, operation: str, unit_name: str) -> EnableResult:
        try:
            stdout, _, _ = await self._run_systemctl(operation, unit_name)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, operation, exc.stderr) from exc

        changes: list[tuple[str, str, str]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                changes.append((
                    parts[0],
                    parts[1] if len(parts) > 1 else "",
                    parts[-1] if len(parts) > 2 else "",
                ))

        return EnableResult(changes=changes)

    async def enable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("enable", unit_name)

    async def disable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("disable", unit_name)

    async def mask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("mask", unit_name)

    async def unmask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("unmask", unit_name)

    async def daemon_reload(self) -> None:
        await self._run_systemctl("daemon-reload")

    async def reset_failed(self, unit_name: str | None = None) -> None:
        args = ["reset-failed"]
        if unit_name:
            args.append(unit_name)
        await self._run_systemctl(*args)

    async def get_unit_file_state(self, unit_name: str) -> str:
        stdout, _, _ = await self._run_systemctl("is-enabled", unit_name, check=False)
        return stdout.strip()

    async def is_active(self, unit_name: str) -> bool:
        _, _, returncode = await self._run_systemctl("is-active", unit_name, check=False)
        return returncode == 0

    async def is_enabled(self, unit_name: str) -> bool:
        _, _, returncode = await self._run_systemctl("is-enabled", unit_name, check=False)
        return returncode == 0

    async def is_failed(self, unit_name: str) -> bool:
        _, _, returncode = await self._run_systemctl("is-failed", unit_name, check=False)
        return returncode == 0

    # ── Unit file install / uninstall / edit ────────────────────

    # ── Environment management ───────────────────────────────

    async def show_environment(self) -> dict[str, str]:
        stdout, _, _ = await self._run_systemctl("show-environment")
        env: dict[str, str] = {}
        for line in stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                env[k] = v
        return env

    async def set_environment(self, variables: dict[str, str]) -> None:
        args = ["set-environment"]
        for k, v in variables.items():
            args.append(f"{k}={v}")
        await self._run_systemctl(*args)

    async def unset_environment(self, names: list[str]) -> None:
        await self._run_systemctl("unset-environment", *names)

    # ── Session management (loginctl) ──────────────────────────

    async def _run_loginctl(self, *args: str) -> str:
        cmd = ["loginctl", *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        if proc.returncode and proc.returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            raise SubprocessError(cmd, proc.returncode, stderr)
        return stdout_bytes.decode("utf-8", errors="replace")

    async def list_sessions(self) -> list[SessionInfo]:
        stdout = await self._run_loginctl("list-sessions", "--no-legend", "--no-pager")
        sessions: list[SessionInfo] = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                sessions.append(SessionInfo(
                    id=parts[0],
                    uid=int(parts[1]) if parts[1].isdigit() else 0,
                    user=parts[2] if len(parts) > 2 else "",
                    seat=parts[3] if len(parts) > 3 else "",
                    tty=parts[4] if len(parts) > 4 else "",
                    state=parts[-1] if len(parts) > 2 else "",
                ))
        return sessions

    async def list_users(self) -> list[UserInfo]:
        stdout = await self._run_loginctl("list-users", "--no-legend", "--no-pager")
        users: list[UserInfo] = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                users.append(UserInfo(
                    uid=int(parts[0]) if parts[0].isdigit() else 0,
                    name=parts[1],
                    state=parts[-1] if len(parts) > 2 else "",
                ))
        return users

    async def terminate_session(self, session_id: str) -> None:
        await self._run_loginctl("terminate-session", session_id)

    async def lock_session(self, session_id: str) -> None:
        await self._run_loginctl("lock-session", session_id)

    # ── Resource control + monitoring ─────────────────────────

    async def set_property(self, unit_name: str, properties: dict[str, str]) -> None:
        args = ["set-property", unit_name]
        for k, v in properties.items():
            args.append(f"{k}={v}")
        try:
            await self._run_systemctl(*args)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "set-property", exc.stderr) from exc

    async def get_resource_usage(self, unit_name: str) -> ResourceUsage:
        stdout, _, _ = await self._run_systemctl(
            "show", unit_name,
            "-p", "CPUUsageNSec,MemoryCurrent,MemoryPeak,"
            "TasksCurrent,IOReadBytes,IOWriteBytes",
            "--no-pager",
        )
        props: dict[str, str] = {}
        for line in stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                props[k.strip()] = v.strip()

        def _val(key: str) -> int | None:
            raw = props.get(key, "")
            if not raw or raw == "[not set]" or raw == "infinity":
                return None
            try:
                v = int(raw)
                return v if v > 0 else None
            except ValueError:
                return None

        return ResourceUsage(
            cpu_usage_nsec=_val("CPUUsageNSec"),
            memory_current=_val("MemoryCurrent"),
            memory_peak=_val("MemoryPeak"),
            tasks_current=_val("TasksCurrent"),
            io_read_bytes=_val("IOReadBytes"),
            io_write_bytes=_val("IOWriteBytes"),
        )

    async def list_timers(self) -> list[TimerInfo]:
        stdout, _, _ = await self._run_systemctl(
            "list-timers", "--output=json", "--no-pager", "--all",
        )
        data = json.loads(stdout) if stdout.strip() else []
        timers: list[TimerInfo] = []
        for entry in data:
            timers.append(TimerInfo(
                name=entry.get("unit", ""),
                time_left=entry.get("left", None),
                unit=entry.get("unit", ""),
                activates=entry.get("activates", None),
            ))
        return timers

    async def list_sockets(self) -> list[SocketInfo]:
        stdout, _, _ = await self._run_systemctl(
            "list-sockets", "--output=json", "--no-pager", "--all",
        )
        data = json.loads(stdout) if stdout.strip() else []
        sockets: list[SocketInfo] = []
        for entry in data:
            sockets.append(SocketInfo(
                name=entry.get("unit", ""),
                listen=entry.get("listen", ""),
                type=entry.get("type", ""),
                unit=entry.get("activates", entry.get("unit", "")),
            ))
        return sockets

    async def list_dependencies(self, unit_name: str) -> list[str]:
        stdout, _, _ = await self._run_systemctl(
            "list-dependencies", unit_name, "--plain", "--no-pager",
        )
        deps: list[str] = []
        for line in stdout.splitlines():
            name = line.strip()
            if name and name != unit_name:
                deps.append(name)
        return deps

    async def kill_unit(self, unit_name: str, signal: str = "SIGTERM") -> None:
        try:
            await self._run_systemctl("kill", unit_name, f"--signal={signal}")
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "kill", exc.stderr) from exc

    # ── Transient units (systemd-run) ─────────────────────────

    async def _run_systemd_run(self, *args: str) -> tuple[str, str, int]:
        cmd = ["systemd-run", self._scope_flag, *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = proc.returncode or 0
        if returncode != 0:
            raise SubprocessError(cmd, returncode, stderr.strip())
        return stdout, stderr, returncode

    def _parse_transient_result(self, stdout: str, stderr: str) -> TransientResult:
        """Parse systemd-run output for unit name and PID."""
        combined = stdout + stderr
        unit_name = ""
        pid = None
        for line in combined.splitlines():
            if "Running as unit:" in line or "Running timer as unit:" in line:
                unit_name = line.split(":")[-1].strip().rstrip(".")
            elif "as PID" in line:
                for part in line.split():
                    if part.isdigit():
                        pid = int(part)
                        break
        return TransientResult(unit_name=unit_name, pid=pid)

    async def run_transient(
        self,
        command: list[str],
        *,
        name: str | None = None,
        properties: dict[str, str] | None = None,
        remain_after_exit: bool = False,
        wait: bool = False,
    ) -> TransientResult:
        args: list[str] = []
        if name:
            args.extend(["--unit", name])
        if remain_after_exit:
            args.append("--remain-after-exit")
        if wait:
            args.append("--wait")
        if properties:
            for k, v in properties.items():
                args.extend(["--property", f"{k}={v}"])
        args.append("--")
        args.extend(command)
        stdout, stderr, _ = await self._run_systemd_run(*args)
        return self._parse_transient_result(stdout, stderr)

    async def run_transient_timer(
        self,
        command: list[str],
        *,
        on_calendar: str | None = None,
        on_active: str | None = None,
        name: str | None = None,
    ) -> TransientResult:
        args: list[str] = []
        if name:
            args.extend(["--unit", name])
        if on_calendar:
            args.extend(["--on-calendar", on_calendar])
        if on_active:
            args.extend(["--on-active", on_active])
        args.append("--")
        args.extend(command)
        stdout, stderr, _ = await self._run_systemd_run(*args)
        return self._parse_transient_result(stdout, stderr)

    # ── Unit file install / uninstall / edit ────────────────────

    async def install_unit_file(self, unit_file: UnitFile) -> str:
        target_dir = unit_file_dir(self._scope)

        def _write() -> str:
            target_dir.mkdir(parents=True, exist_ok=True)
            path = target_dir / unit_file.name
            path.write_text(unit_file.content, encoding="utf-8")
            return str(path)

        try:
            written = await asyncio.to_thread(_write)
        except OSError as exc:
            raise UnitFileInstallError(unit_file.name, "install", str(exc)) from exc

        await self.daemon_reload()
        return written

    async def uninstall_unit_file(self, unit_name: str) -> None:
        target_dir = unit_file_dir(self._scope)
        unit_path = target_dir / unit_name
        dropin_dir = target_dir / f"{unit_name}.d"

        def _remove() -> None:
            if not unit_path.exists():
                raise FileNotFoundError(unit_name)
            unit_path.unlink()
            if dropin_dir.is_dir():
                shutil.rmtree(dropin_dir)

        try:
            await asyncio.to_thread(_remove)
        except FileNotFoundError as exc:
            raise UnitNotFoundError(unit_name) from exc
        except OSError as exc:
            raise UnitFileInstallError(unit_name, "uninstall", str(exc)) from exc

        await self.daemon_reload()

    async def edit_unit_file(
        self,
        unit_name: str,
        overrides: dict[str, dict[str, str]],
    ) -> str:
        target_dir = unit_file_dir(self._scope)
        dropin_dir = target_dir / f"{unit_name}.d"

        def _write_override() -> str:
            dropin_dir.mkdir(parents=True, exist_ok=True)
            override_path = dropin_dir / "override.conf"
            lines: list[str] = []
            for section, kvs in overrides.items():
                lines.append(f"[{section}]")
                for key, value in kvs.items():
                    lines.append(f"{key}={value}")
                lines.append("")
            override_path.write_text("\n".join(lines), encoding="utf-8")
            return str(override_path)

        try:
            written = await asyncio.to_thread(_write_override)
        except OSError as exc:
            raise UnitFileInstallError(unit_name, "edit", str(exc)) from exc

        await self.daemon_reload()
        return written

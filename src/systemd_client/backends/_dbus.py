"""DBus backend using dasbus (optional dependency)."""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from systemd_client._unit_escape import unit_dbus_object_path
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

try:
    from dasbus.connection import SessionMessageBus, SystemMessageBus
    from dasbus.typing import get_native
except ImportError as _exc:
    raise ImportError(
        "dasbus is required for the DBus backend. "
        "Install with: pip install systemd-client[dbus]"
    ) from _exc


_MANAGER_IFACE = "org.freedesktop.systemd1.Manager"
_UNIT_IFACE = "org.freedesktop.systemd1.Unit"
_SERVICE_IFACE = "org.freedesktop.systemd1.Service"
_SYSTEMD_PATH = "/org/freedesktop/systemd1"
_SYSTEMD_BUS_NAME = "org.freedesktop.systemd1"


class DBusBackend(AbstractBackend):
    """Backend that communicates via D-Bus using dasbus."""

    def __init__(self, scope: SystemdScope = SystemdScope.USER) -> None:
        self._scope = scope
        if scope == SystemdScope.SYSTEM:
            self._bus = SystemMessageBus()
        else:
            self._bus = SessionMessageBus()
        self._manager = self._bus.get_proxy(_SYSTEMD_BUS_NAME, _SYSTEMD_PATH)

    def _get_unit_proxy(self, unit_name: str) -> Any:
        path = unit_dbus_object_path(unit_name)
        return self._bus.get_proxy(_SYSTEMD_BUS_NAME, path)

    async def list_units(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitInfo]:
        raw_units = await asyncio.to_thread(self._manager.ListUnits)
        units: list[UnitInfo] = []
        for unit_data in get_native(raw_units):
            name = unit_data[0]
            if unit_type and not name.endswith(f".{unit_type}"):
                continue

            try:
                active_state = ActiveState(unit_data[3])
            except ValueError:
                active_state = ActiveState.INACTIVE

            if state and active_state.value != state:
                continue

            try:
                load_state = LoadState(unit_data[2])
            except ValueError:
                load_state = LoadState.LOADED

            try:
                sub_state = SubState(unit_data[4])
            except ValueError:
                sub_state = SubState.DEAD

            units.append(UnitInfo(
                name=name,
                description=unit_data[1],
                load_state=load_state,
                active_state=active_state,
                sub_state=sub_state,
            ))
        return units

    async def list_unit_files(
        self,
        unit_type: str | None = None,
        state: str | None = None,
    ) -> list[UnitFileInfo]:
        raw_files = await asyncio.to_thread(self._manager.ListUnitFiles)
        files: list[UnitFileInfo] = []
        for file_data in get_native(raw_files):
            name = file_data[0]
            raw_state = file_data[1]

            if unit_type and not name.endswith(f".{unit_type}"):
                continue

            try:
                file_state = UnitFileState(raw_state)
            except ValueError:
                continue

            if state and file_state.value != state:
                continue

            # Use just the filename, not the full path
            short_name = name.rsplit("/", 1)[-1] if "/" in name else name
            files.append(UnitFileInfo(name=short_name, state=file_state))
        return files

    async def get_unit_status(self, unit_name: str) -> UnitStatus:
        try:
            proxy = await asyncio.to_thread(self._get_unit_proxy, unit_name)
            props = await asyncio.to_thread(lambda: {
                "Id": proxy.Id,
                "Description": proxy.Description,
                "LoadState": proxy.LoadState,
                "ActiveState": proxy.ActiveState,
                "SubState": proxy.SubState,
                "UnitFileState": proxy.UnitFileState,
                "FragmentPath": proxy.FragmentPath,
                "MainPID": proxy.MainPID,
                "ExecMainStatus": proxy.ExecMainStatus,
                "Result": proxy.Result,
                "ActiveEnterTimestamp": proxy.ActiveEnterTimestamp,
                "ActiveExitTimestamp": proxy.ActiveExitTimestamp,
                "InactiveEnterTimestamp": proxy.InactiveEnterTimestamp,
                "InactiveExitTimestamp": proxy.InactiveExitTimestamp,
            })
        except Exception as exc:
            error_msg = str(exc).lower()
            if "no such unit" in error_msg or "not found" in error_msg:
                raise UnitNotFoundError(unit_name) from exc
            raise

        native_props = get_native(props)

        if native_props.get("LoadState") == "not-found":
            raise UnitNotFoundError(unit_name)

        def _safe_enum(cls: type, val: str, default: str) -> Any:
            try:
                return cls(val)
            except ValueError:
                return cls(default)

        def _usec_to_datetime(usec: Any) -> datetime | None:
            try:
                val = int(usec)
                if val == 0:
                    return None
                return datetime.fromtimestamp(val / 1_000_000, tz=UTC)
            except (ValueError, OSError, TypeError):
                return None

        main_pid = native_props.get("MainPID")
        main_pid = main_pid if main_pid and main_pid != 0 else None

        exec_main_status = native_props.get("ExecMainStatus")
        if exec_main_status is not None:
            try:
                exec_main_status = int(exec_main_status)
            except (ValueError, TypeError):
                exec_main_status = None

        return UnitStatus(
            name=native_props.get("Id", unit_name),
            description=native_props.get("Description", ""),
            load_state=_safe_enum(LoadState, native_props.get("LoadState", "loaded"), "loaded"),
            active_state=_safe_enum(
                ActiveState, native_props.get("ActiveState", "inactive"), "inactive",
            ),
            sub_state=_safe_enum(
                SubState, native_props.get("SubState", "dead"), "dead",
            ),
            unit_file_state=(
                _safe_enum(UnitFileState, native_props["UnitFileState"], "disabled")
                if native_props.get("UnitFileState") else None
            ),
            fragment_path=native_props.get("FragmentPath") or None,
            active_enter_timestamp=_usec_to_datetime(native_props.get("ActiveEnterTimestamp")),
            active_exit_timestamp=_usec_to_datetime(native_props.get("ActiveExitTimestamp")),
            inactive_enter_timestamp=_usec_to_datetime(
                native_props.get("InactiveEnterTimestamp"),
            ),
            inactive_exit_timestamp=_usec_to_datetime(
                native_props.get("InactiveExitTimestamp"),
            ),
            main_pid=main_pid,
            exec_main_status=exec_main_status,
            result=native_props.get("Result") or None,
            properties={k: str(v) for k, v in native_props.items()},
        )

    async def cat(self, unit_name: str) -> str:
        try:
            proxy = await asyncio.to_thread(self._get_unit_proxy, unit_name)
            fragment = await asyncio.to_thread(lambda: get_native(proxy.FragmentPath))
        except Exception as exc:
            error_msg = str(exc).lower()
            if "no such unit" in error_msg or "not found" in error_msg:
                raise UnitNotFoundError(unit_name) from exc
            raise

        if not fragment:
            raise UnitNotFoundError(unit_name)

        def _read_file(path: str) -> str:
            with open(path) as f:
                return f.read()

        return await asyncio.to_thread(_read_file, fragment)

    async def _unit_action(self, unit_name: str, action: str) -> None:
        method = getattr(self._manager, f"{action}Unit")
        try:
            await asyncio.to_thread(method, unit_name, "replace")
        except Exception as exc:
            raise UnitOperationError(unit_name, action.lower(), str(exc)) from exc

    async def start_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "Start")

    async def stop_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "Stop")

    async def restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "Restart")

    async def reload_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "Reload")

    async def try_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "TryRestart")

    async def reload_or_restart_unit(self, unit_name: str, no_block: bool = False) -> None:
        await self._unit_action(unit_name, "ReloadOrRestart")

    async def start_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await asyncio.gather(*(self.start_unit(n) for n in unit_names))

    async def stop_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await asyncio.gather(*(self.stop_unit(n) for n in unit_names))

    async def restart_units(self, unit_names: list[str], no_block: bool = False) -> None:
        await asyncio.gather(*(self.restart_unit(n) for n in unit_names))

    async def _enable_op(self, method_name: str, unit_name: str) -> EnableResult:
        method = getattr(self._manager, method_name)
        try:
            no_install = ("MaskUnitFiles", "UnmaskUnitFiles", "DisableUnitFiles")
            if method_name in no_install:
                result = await asyncio.to_thread(method, [unit_name], False)
            else:
                result = await asyncio.to_thread(method, [unit_name], False, True)
        except Exception as exc:
            raise UnitOperationError(unit_name, method_name, str(exc)) from exc

        native = get_native(result)
        # EnableUnitFiles returns (carries_install_info, changes)
        # DisableUnitFiles returns (changes,)
        if isinstance(native, tuple) and len(native) == 2 and isinstance(native[0], bool):
            carries = native[0]
            raw_changes = native[1]
        elif isinstance(native, tuple) and len(native) == 1:
            carries = False
            raw_changes = native[0]
        else:
            carries = False
            raw_changes = native if isinstance(native, list) else []

        changes = [
            (str(c[0]), str(c[1]), str(c[2]) if len(c) > 2 else "")
            for c in raw_changes
        ] if raw_changes else []

        return EnableResult(changes=changes, carries_install_info=carries)

    async def enable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_op("EnableUnitFiles", unit_name)

    async def disable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_op("DisableUnitFiles", unit_name)

    async def mask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_op("MaskUnitFiles", unit_name)

    async def unmask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_op("UnmaskUnitFiles", unit_name)

    async def daemon_reload(self) -> None:
        await asyncio.to_thread(self._manager.Reload)

    async def reset_failed(self, unit_name: str | None = None) -> None:
        if unit_name:
            await asyncio.to_thread(self._manager.ResetFailedUnit, unit_name)
        else:
            await asyncio.to_thread(self._manager.ResetFailed)

    async def get_unit_file_state(self, unit_name: str) -> str:
        result = await asyncio.to_thread(self._manager.GetUnitFileState, unit_name)
        return str(get_native(result))

    async def is_active(self, unit_name: str) -> bool:
        try:
            proxy = await asyncio.to_thread(self._get_unit_proxy, unit_name)
            state = await asyncio.to_thread(lambda: get_native(proxy.ActiveState))
            return state == "active"
        except Exception:
            return False

    async def is_enabled(self, unit_name: str) -> bool:
        try:
            state = await self.get_unit_file_state(unit_name)
            return state in ("enabled", "enabled-runtime", "static", "indirect", "generated")
        except Exception:
            return False

    async def is_failed(self, unit_name: str) -> bool:
        try:
            proxy = await asyncio.to_thread(self._get_unit_proxy, unit_name)
            state = await asyncio.to_thread(lambda: get_native(proxy.ActiveState))
            return state == "failed"
        except Exception:
            return False

    # ── Environment management ───────────────────────────────

    async def show_environment(self) -> dict[str, str]:
        result = await asyncio.to_thread(self._manager.Environment)
        env: dict[str, str] = {}
        for item in get_native(result):
            if "=" in item:
                k, _, v = item.partition("=")
                env[k] = v
        return env

    async def set_environment(self, variables: dict[str, str]) -> None:
        assignments = [f"{k}={v}" for k, v in variables.items()]
        await asyncio.to_thread(self._manager.SetEnvironment, assignments)

    async def unset_environment(self, names: list[str]) -> None:
        await asyncio.to_thread(self._manager.UnsetEnvironment, names)

    # ── Session management (loginctl subprocess) ───────────────

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
        stdout = await self._run_loginctl("list-sessions", "--output=json", "--no-pager")
        import json
        data = json.loads(stdout) if stdout.strip() else []
        return [
            SessionInfo(
                id=str(s.get("session", "")), uid=int(s.get("uid", 0)),
                user=s.get("user", ""), seat=s.get("seat", ""),
                tty=s.get("tty", ""), state=s.get("state", ""),
            )
            for s in data
        ]

    async def list_users(self) -> list[UserInfo]:
        stdout = await self._run_loginctl("list-users", "--output=json", "--no-pager")
        import json
        data = json.loads(stdout) if stdout.strip() else []
        return [
            UserInfo(uid=int(u.get("uid", 0)), name=u.get("user", ""), state=u.get("state", ""))
            for u in data
        ]

    async def terminate_session(self, session_id: str) -> None:
        await self._run_loginctl("terminate-session", session_id)

    async def lock_session(self, session_id: str) -> None:
        await self._run_loginctl("lock-session", session_id)

    # ── Resource control + monitoring ─────────────────────────

    async def set_property(self, unit_name: str, properties: dict[str, str]) -> None:
        try:
            for k, v in properties.items():
                await asyncio.to_thread(
                    self._manager.SetUnitProperties, unit_name, True, [(k, v)],
                )
        except Exception as exc:
            raise UnitOperationError(unit_name, "set-property", str(exc)) from exc

    async def get_resource_usage(self, unit_name: str) -> ResourceUsage:
        try:
            proxy = await asyncio.to_thread(self._get_unit_proxy, unit_name)
            props = await asyncio.to_thread(lambda: {
                "CPUUsageNSec": proxy.CPUUsageNSec,
                "MemoryCurrent": proxy.MemoryCurrent,
                "TasksCurrent": proxy.TasksCurrent,
            })
            native = get_native(props)

            def _val(key: str) -> int | None:
                v = native.get(key)
                if v is None or v == 0xFFFFFFFFFFFFFFFF:  # uint64 max = not set
                    return None
                val = int(v)
                return val if val > 0 else None

            return ResourceUsage(
                cpu_usage_nsec=_val("CPUUsageNSec"),
                memory_current=_val("MemoryCurrent"),
                tasks_current=_val("TasksCurrent"),
            )
        except Exception:
            return ResourceUsage()

    async def list_timers(self) -> list[TimerInfo]:
        # Use subprocess fallback — no clean D-Bus API for list-timers
        scope_flag = f"--{self._scope.value}"
        cmd = ["systemctl", scope_flag, "list-timers", "--output=json", "--no-pager", "--all"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        import json
        data = json.loads(stdout) if stdout.strip() else []
        return [
            TimerInfo(
                name=e.get("unit", ""), time_left=e.get("left"),
                unit=e.get("unit", ""), activates=e.get("activates"),
            )
            for e in data
        ]

    async def list_sockets(self) -> list[SocketInfo]:
        scope_flag = f"--{self._scope.value}"
        cmd = ["systemctl", scope_flag, "list-sockets", "--output=json", "--no-pager", "--all"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        import json
        data = json.loads(stdout) if stdout.strip() else []
        return [
            SocketInfo(
                name=e.get("unit", ""), listen=e.get("listen", ""),
                type=e.get("type", ""), unit=e.get("activates", e.get("unit", "")),
            )
            for e in data
        ]

    async def list_dependencies(self, unit_name: str) -> list[str]:
        scope_flag = f"--{self._scope.value}"
        cmd = ["systemctl", scope_flag, "list-dependencies", unit_name, "--plain", "--no-pager"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        return [
            line.strip() for line in stdout.splitlines()
            if line.strip() and line.strip() != unit_name
        ]

    async def kill_unit(self, unit_name: str, signal: str = "SIGTERM") -> None:
        try:
            await asyncio.to_thread(self._manager.KillUnit, unit_name, "all", signal)
        except Exception as exc:
            raise UnitOperationError(unit_name, "kill", str(exc)) from exc

    # ── Transient units (systemd-run via subprocess) ──────────

    async def _run_systemd_run(self, *args: str) -> tuple[str, str, int]:
        scope_flag = f"--{self._scope.value}"
        cmd = ["systemd-run", scope_flag, *args]
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

    async def close(self) -> None:
        self._bus.disconnect()

"""Subprocess backend: communicates with systemd via systemctl --user."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from systemd_client.backends._base import AbstractBackend
from systemd_client.enums import ActiveState, LoadState, SubState, UnitFileState
from systemd_client.exceptions import (
    SubprocessError,
    UnitNotFoundError,
    UnitOperationError,
)
from systemd_client.models import EnableResult, UnitInfo, UnitStatus


class SubprocessBackend(AbstractBackend):
    """Backend that uses systemctl/journalctl subprocess calls."""

    async def _run_systemctl(self, *args: str, check: bool = True) -> tuple[str, str, int]:
        """Run a systemctl --user command and return (stdout, stderr, returncode)."""
        cmd = ["systemctl", "--user", *args]
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
                    return datetime.fromtimestamp(int(raw_usec) / 1_000_000, tz=timezone.utc)
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

        def _safe_int(key: str) -> int | None:
            raw = props.get(key, "")
            if not raw or raw == "0":
                return None
            try:
                val = int(raw)
                return val if val != 0 else None
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
            unit_file_state=_safe_enum(UnitFileState, "UnitFileState", "disabled") if props.get("UnitFileState") else None,  # type: ignore[arg-type]
            fragment_path=props.get("FragmentPath") or None,
            active_enter_timestamp=_parse_timestamp("ActiveEnterTimestamp"),
            active_exit_timestamp=_parse_timestamp("ActiveExitTimestamp"),
            inactive_enter_timestamp=_parse_timestamp("InactiveEnterTimestamp"),
            inactive_exit_timestamp=_parse_timestamp("InactiveExitTimestamp"),
            main_pid=_safe_int("MainPID"),
            exec_main_status=_safe_int("ExecMainStatus"),
            result=props.get("Result") or None,
            triggered_by=triggered_by,
            documentation=documentation,
            properties=props,
        )

    async def start_unit(self, unit_name: str) -> None:
        try:
            await self._run_systemctl("start", unit_name)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "start", exc.stderr) from exc

    async def stop_unit(self, unit_name: str) -> None:
        try:
            await self._run_systemctl("stop", unit_name)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "stop", exc.stderr) from exc

    async def restart_unit(self, unit_name: str) -> None:
        try:
            await self._run_systemctl("restart", unit_name)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "restart", exc.stderr) from exc

    async def reload_unit(self, unit_name: str) -> None:
        try:
            await self._run_systemctl("reload", unit_name)
        except SubprocessError as exc:
            raise UnitOperationError(unit_name, "reload", exc.stderr) from exc

    async def enable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("enable", unit_name)

    async def disable_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("disable", unit_name)

    async def mask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("mask", unit_name)

    async def unmask_unit(self, unit_name: str) -> EnableResult:
        return await self._enable_disable_op("unmask", unit_name)

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
            # Typical output: "Created symlink /path/to -> /path/from"
            # or "Removed /path"
            parts = line.split()
            if len(parts) >= 2:
                changes.append((parts[0], parts[1] if len(parts) > 1 else "", parts[-1] if len(parts) > 2 else ""))

        return EnableResult(changes=changes)

    async def daemon_reload(self) -> None:
        await self._run_systemctl("daemon-reload")

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

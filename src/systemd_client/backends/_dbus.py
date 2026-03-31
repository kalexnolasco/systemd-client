"""DBus backend using dasbus (optional dependency)."""

from __future__ import annotations

import asyncio
from typing import Any

from systemd_client._unit_escape import unit_dbus_object_path
from systemd_client.backends._base import AbstractBackend
from systemd_client.enums import ActiveState, LoadState, SubState, UnitFileState
from systemd_client.exceptions import UnitNotFoundError, UnitOperationError
from systemd_client.models import EnableResult, UnitInfo, UnitStatus

try:
    from dasbus.connection import SessionMessageBus
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

    def __init__(self) -> None:
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
                "Result": proxy.Result,
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

        return UnitStatus(
            name=native_props.get("Id", unit_name),
            description=native_props.get("Description", ""),
            load_state=_safe_enum(LoadState, native_props.get("LoadState", "loaded"), "loaded"),
            active_state=_safe_enum(ActiveState, native_props.get("ActiveState", "inactive"), "inactive"),
            sub_state=_safe_enum(SubState, native_props.get("SubState", "dead"), "dead"),
            unit_file_state=_safe_enum(UnitFileState, native_props["UnitFileState"], "disabled") if native_props.get("UnitFileState") else None,
            fragment_path=native_props.get("FragmentPath") or None,
            main_pid=native_props.get("MainPID") or None,
            result=native_props.get("Result") or None,
            properties={k: str(v) for k, v in native_props.items()},
        )

    async def _unit_action(self, unit_name: str, action: str) -> None:
        method = getattr(self._manager, f"{action}Unit")
        try:
            await asyncio.to_thread(method, unit_name, "replace")
        except Exception as exc:
            raise UnitOperationError(unit_name, action.lower(), str(exc)) from exc

    async def start_unit(self, unit_name: str) -> None:
        await self._unit_action(unit_name, "Start")

    async def stop_unit(self, unit_name: str) -> None:
        await self._unit_action(unit_name, "Stop")

    async def restart_unit(self, unit_name: str) -> None:
        await self._unit_action(unit_name, "Restart")

    async def reload_unit(self, unit_name: str) -> None:
        await self._unit_action(unit_name, "Reload")

    async def _enable_op(self, method_name: str, unit_name: str) -> EnableResult:
        method = getattr(self._manager, method_name)
        try:
            if method_name in ("MaskUnitFiles", "UnmaskUnitFiles"):
                result = await asyncio.to_thread(method, [unit_name], False)
            elif method_name == "DisableUnitFiles":
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

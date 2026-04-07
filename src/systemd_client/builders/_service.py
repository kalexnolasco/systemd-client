"""ServiceBuilder for creating .service unit files."""

from __future__ import annotations

from typing import Self

from systemd_client.builders._base import _BaseBuilder
from systemd_client.builders._validation import validate_absolute_path
from systemd_client.enums import UnitType


class ServiceBuilder(_BaseBuilder):
    """Fluent builder for systemd service unit files."""

    def __init__(self, name: str, *, template: bool = False) -> None:
        super().__init__(name, UnitType.SERVICE, template=template)

    # ── [Service] section ───────────────────────────────────────

    def type_(self, svc_type: str) -> Self:
        self._set(self._type_section, "Type", svc_type)
        return self

    def exec_start(self, cmd: str) -> Self:
        self._set(self._type_section, "ExecStart", cmd)
        return self

    def exec_start_pre(self, cmd: str) -> Self:
        self._append(self._type_section, "ExecStartPre", cmd)
        return self

    def exec_start_post(self, cmd: str) -> Self:
        self._append(self._type_section, "ExecStartPost", cmd)
        return self

    def exec_stop(self, cmd: str) -> Self:
        self._set(self._type_section, "ExecStop", cmd)
        return self

    def exec_stop_post(self, cmd: str) -> Self:
        self._append(self._type_section, "ExecStopPost", cmd)
        return self

    def exec_reload(self, cmd: str) -> Self:
        self._set(self._type_section, "ExecReload", cmd)
        return self

    def restart(self, policy: str) -> Self:
        self._set(self._type_section, "Restart", policy)
        return self

    def restart_sec(self, seconds: int | float) -> Self:
        self._set(self._type_section, "RestartSec", str(seconds))
        return self

    def timeout_start_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "TimeoutStartSec", str(seconds))
        return self

    def timeout_stop_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "TimeoutStopSec", str(seconds))
        return self

    def watchdog_sec(self, seconds: int) -> Self:
        self._set(self._type_section, "WatchdogSec", str(seconds))
        return self

    def user(self, name: str) -> Self:
        self._set(self._type_section, "User", name)
        return self

    def group(self, name: str) -> Self:
        self._set(self._type_section, "Group", name)
        return self

    def working_directory(self, path: str) -> Self:
        self._set(self._type_section, "WorkingDirectory", path)
        return self

    def environment(self, env: dict[str, str]) -> Self:
        quoted = " ".join(f'"{k}={v}"' for k, v in env.items())
        self._set(self._type_section, "Environment", quoted)
        return self

    def environment_file(self, path: str) -> Self:
        self._append(self._type_section, "EnvironmentFile", path)
        return self

    def standard_output(self, target: str) -> Self:
        self._set(self._type_section, "StandardOutput", target)
        return self

    def standard_error(self, target: str) -> Self:
        self._set(self._type_section, "StandardError", target)
        return self

    def runtime_directory(self, name: str) -> Self:
        self._set(self._type_section, "RuntimeDirectory", name)
        return self

    def state_directory(self, name: str) -> Self:
        self._set(self._type_section, "StateDirectory", name)
        return self

    def syslog_identifier(self, name: str) -> Self:
        self._set(self._type_section, "SyslogIdentifier", name)
        return self

    def remain_after_exit(self, val: bool) -> Self:
        self._set(self._type_section, "RemainAfterExit", "true" if val else "false")
        return self

    def pid_file(self, path: str) -> Self:
        self._set(self._type_section, "PIDFile", path)
        return self

    def nice(self, n: int) -> Self:
        self._set(self._type_section, "Nice", str(n))
        return self

    def limit_nofile(self, n: int) -> Self:
        self._set(self._type_section, "LimitNOFILE", str(n))
        return self

    def private_tmp(self, val: bool) -> Self:
        self._set(self._type_section, "PrivateTmp", "true" if val else "false")
        return self

    def protect_system(self, val: str) -> Self:
        self._set(self._type_section, "ProtectSystem", val)
        return self

    def protect_home(self, val: str) -> Self:
        self._set(self._type_section, "ProtectHome", val)
        return self

    def dynamic_user(self, val: bool) -> Self:
        self._set(self._type_section, "DynamicUser", "true" if val else "false")
        return self

    # ── Validation ──────────────────────────────────────────────

    def _validate(self) -> None:
        errors: list[str] = []

        if "ExecStart" not in self._type_section:
            errors.append("ExecStart is required for service units")

        wd = self._type_section.get("WorkingDirectory")
        if wd:
            err = validate_absolute_path(wd[0], "WorkingDirectory")
            if err:
                errors.append(err)

        self._raise_validation(errors)

"""systemd-analyze wrapper for boot analysis and security scoring."""

from __future__ import annotations

import asyncio
import json
import re

from systemd_client.enums import SystemdScope  # noqa: TC001
from systemd_client.exceptions import SubprocessError
from systemd_client.models import BlameEntry, SecurityAnalysis, SecurityIssue


async def _run_analyze(scope: SystemdScope, *args: str) -> str:
    """Run systemd-analyze with scope flag and return stdout."""
    cmd = ["systemd-analyze", f"--{scope.value}", *args]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    if proc.returncode and proc.returncode != 0:
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        raise SubprocessError(cmd, proc.returncode, stderr)
    return stdout_bytes.decode("utf-8", errors="replace")


async def analyze_blame(scope: SystemdScope) -> list[BlameEntry]:
    """Parse systemd-analyze blame output into BlameEntry list."""
    stdout = await _run_analyze(scope, "blame", "--no-pager")
    entries: list[BlameEntry] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "32.875s pmlogger.service" or "245ms dbus.service"
        match = re.match(r"^\s*([\d.]+)(min|s|ms|us)\s+(.+)$", line)
        if match:
            val, unit_str, name = match.groups()
            multipliers = {"us": 1, "ms": 1000, "s": 1_000_000, "min": 60_000_000}
            time_us = int(float(val) * multipliers.get(unit_str, 1))
            entries.append(BlameEntry(time_us=time_us, unit=name))
    return entries


async def analyze_critical_chain(scope: SystemdScope, unit: str | None = None) -> str:
    """Return systemd-analyze critical-chain output as raw text."""
    args = ["critical-chain", "--no-pager"]
    if unit:
        args.append(unit)
    return await _run_analyze(scope, *args)


async def analyze_security(scope: SystemdScope, unit: str) -> SecurityAnalysis:
    """Parse systemd-analyze security output for a specific unit."""
    stdout = await _run_analyze(scope, "security", "--json=short", unit)
    data = json.loads(stdout) if stdout.strip() else []

    # JSON output is a list of unit analyses
    for entry in data:
        if entry.get("unit", "") == unit or len(data) == 1:
            exposure = float(entry.get("exposure", 10.0))
            issues: list[SecurityIssue] = []
            for pred in entry.get("predicates", []):
                issues.append(SecurityIssue(
                    id=pred.get("set_name", ""),
                    description=pred.get("description", ""),
                    severity=pred.get("badness_description", ""),
                    value=pred.get("value", ""),
                ))
            return SecurityAnalysis(unit=unit, exposure=exposure, issues=issues)

    return SecurityAnalysis(unit=unit, exposure=10.0)


async def analyze_verify(scope: SystemdScope, unit: str) -> list[str]:
    """Run systemd-analyze verify and return diagnostic messages."""
    try:
        stdout = await _run_analyze(scope, "verify", unit)
    except SubprocessError as exc:
        # verify returns non-zero on warnings, but stderr has the messages
        return [line for line in exc.stderr.splitlines() if line.strip()]
    return [line for line in stdout.splitlines() if line.strip()]

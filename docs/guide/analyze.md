# System Analysis

systemd-client wraps `systemd-analyze` to give you **boot performance profiling**, **security auditing**, **unit verification**, and **critical chain analysis** -- all from Python.

Let's walk through each analysis tool.

## Boot Blame

Find out which units are slowing down your boot with `analyze_blame()`:

```python hl_lines="4 7 8"
from systemd_client import SystemdClient

client = SystemdClient()
entries = client.analyze_blame()  # (1)!

# Top 10 slowest units
for entry in entries[:10]:  # (2)!
    seconds = entry.time_us / 1_000_000
    print(f"  {seconds:>8.3f}s  {entry.unit}")
```

1. Returns a `list[BlameEntry]` sorted by initialization time, slowest first.
2. Each `BlameEntry` has `time_us` (microseconds) and `unit` (the unit name).

```console
$ python blame.py
    32.875s  pmlogger.service
    12.456s  NetworkManager-wait-online.service
     8.234s  docker.service
     5.678s  postgresql.service
     3.456s  nginx.service
     2.345s  snapd.service
     1.234s  ssh.service
     0.987s  systemd-journal-flush.service
     0.654s  systemd-tmpfiles-setup.service
     0.321s  dbus.service
```

!!! tip
    Focus your optimization efforts on the top entries. A service that takes 30+ seconds to start is often waiting on a network dependency or misconfigured timeout.

### BlameEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `time_us` | `int` | Initialization time in microseconds |
| `unit` | `str` | Unit name |

### Example: Find Units Slower Than N Seconds

```python hl_lines="4 5"
from systemd_client import SystemdClient

client = SystemdClient()
slow = [e for e in client.analyze_blame() if e.time_us > 5_000_000]  # (1)!
print(f"{len(slow)} units took more than 5 seconds to start:")
for entry in slow:
    print(f"  {entry.time_us / 1e6:.1f}s  {entry.unit}")
```

1. Filter entries where `time_us` exceeds 5 million microseconds (5 seconds).

## Security Analysis

Audit the security hardening of any service unit with `analyze_security()`:

```python hl_lines="4 7 8 11 12 13"
from systemd_client import SystemdClient

client = SystemdClient()
analysis = client.analyze_security("my-app.service")  # (1)!

# Exposure score: 0.0 (fully hardened) to 10.0 (no hardening)
print(f"Unit:     {analysis.unit}")
print(f"Exposure: {analysis.exposure:.1f}/10.0")  # (2)!

# Individual issues
for issue in analysis.issues[:10]:
    print(f"  [{issue.severity}] {issue.description}")
    print(f"    Current value: {issue.value}")
```

1. Returns a `SecurityAnalysis` with an overall exposure score and a list of individual issues.
2. Lower is better. Score ranges: `0-2` excellent, `2-5` medium, `5-10` needs attention.

```console
$ python security.py
Unit:     my-app.service
Exposure: 7.2/10.0
  [MEDIUM] PrivateTmp is not set
    Current value: no
  [MEDIUM] ProtectSystem is not set
    Current value: no
  [LOW] NoNewPrivileges is not set
    Current value: no
```

### Interpreting Exposure Scores

| Score | Rating | Action |
|-------|--------|--------|
| 0.0 - 2.0 | Excellent | Fully hardened, no changes needed |
| 2.0 - 5.0 | Medium | Review flagged issues |
| 5.0 - 7.5 | Exposed | Apply recommended hardening directives |
| 7.5 - 10.0 | Unsafe | Immediate attention needed |

!!! info
    The score is calculated by systemd based on which security directives are set in the unit file. Directives like `PrivateTmp=`, `ProtectSystem=`, `NoNewPrivileges=`, and `CapabilityBoundingSet=` all contribute to a lower (better) score.

### SecurityAnalysis Fields

| Field | Type | Description |
|-------|------|-------------|
| `unit` | `str` | Unit name |
| `exposure` | `float` | Overall exposure score (0.0--10.0) |
| `issues` | `list[SecurityIssue]` | Individual security findings |

### SecurityIssue Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Issue identifier |
| `description` | `str` | Human-readable description |
| `severity` | `str` | Severity level (e.g., `"MEDIUM"`, `"LOW"`) |
| `value` | `str` | Current value of the setting |

### Example: Audit All Active Services

```python hl_lines="8 9 10 11 12"
from systemd_client import SystemdClient

client = SystemdClient()
services = client.list_units(unit_type="service", state="active")

print(f"{'Unit':<40} {'Score':>6}")
print("-" * 48)
for svc in services:
    try:
        analysis = client.analyze_security(svc.name)
        score = analysis.exposure
        indicator = "!!" if score >= 7 else ".." if score >= 4 else "ok"
        print(f"{svc.name:<40} {score:>5.1f} {indicator}")
    except Exception:
        print(f"{svc.name:<40}   N/A")
```

!!! warning
    Security analysis requires the unit file to be on disk. It will not work for transient units or units that have been masked.

## Unit Verification

Validate unit file syntax and configuration before deploying with `analyze_verify()`:

```python hl_lines="4 6 7 8 9"
from systemd_client import SystemdClient

client = SystemdClient()
messages = client.analyze_verify("my-app.service")  # (1)!

if not messages:
    print("my-app.service: OK")  # (2)!
else:
    print(f"Found {len(messages)} issue(s):")
    for msg in messages:
        print(f"  {msg}")
```

1. Returns a `list[str]` of diagnostic messages. An empty list means the unit file is valid.
2. A clean verification means the unit file has no syntax errors and all referenced paths/units exist.

```console
$ python verify.py
Found 2 issue(s):
  my-app.service: Unknown key name 'ExecStrat' in section 'Service'
  my-app.service: Unit configured to use Type=notify, but no WatchdogSec= setting
```

### Pre-Deploy Check Pattern

Use verification as a gate before deploying new unit files:

```python hl_lines="8 10 11 12 13"
from systemd_client import SystemdClient, ServiceBuilder

def safe_deploy(name: str, exec_cmd: str) -> bool:
    client = SystemdClient()

    # Build and install
    unit = ServiceBuilder(name).exec_start(exec_cmd).wanted_by("default.target").build()
    path = client.install(unit)

    # Verify before enabling
    messages = client.analyze_verify(f"{name}.service")
    if messages:
        print(f"Verification failed for {name}.service:")
        for msg in messages:
            print(f"  {msg}")
        client.uninstall(f"{name}.service")  # (1)!
        return False

    # All good -- enable and start
    client.daemon_reload()
    client.enable(f"{name}.service")
    client.start(f"{name}.service")
    print(f"Deployed {name}.service from {path}")
    return True
```

1. If verification fails, clean up by removing the unit file immediately.

!!! tip
    Always run `analyze_verify()` after installing a unit file and before enabling it. This catches typos and configuration errors before they cause runtime failures.

## Critical Chain

Visualize the **critical path** of unit startup -- the chain of units that determined boot time:

```python hl_lines="4 5 8"
from systemd_client import SystemdClient

client = SystemdClient()
# Full critical chain
chain = client.analyze_critical_chain()  # (1)!
print(chain)

# Critical chain for a specific unit
chain = client.analyze_critical_chain("my-app.service")  # (2)!
print(chain)
```

1. Returns the raw text output from `systemd-analyze critical-chain`. Shows the tree of dependencies that formed the longest startup path.
2. Pass a unit name to see the critical chain leading to that specific unit.

```console
$ python critical_chain.py
The time when unit became active or started is printed after the "@" character.
The time the unit took to start is printed after the "+" character.

graphical.target @12.345s
  multi-user.target @12.300s
    my-app.service @8.100s +4.200s
      network-online.target @7.900s
        NetworkManager-wait-online.service @2.100s +5.800s
```

!!! info
    The critical chain shows you **why** your system took as long as it did to boot. Each line shows when the unit became active (`@`) and how long it took (`+`). The chain always ends at the unit that completed last.

## Putting It Together: Full System Audit

Here's a complete audit script that combines all four analysis tools:

```python hl_lines="7 13 21 27"
from systemd_client import SystemdClient

def full_audit() -> None:
    client = SystemdClient()

    # 1. Boot performance
    print("=== Boot Blame (Top 5) ===")
    for entry in client.analyze_blame()[:5]:
        print(f"  {entry.time_us / 1e6:>8.3f}s  {entry.unit}")

    print()

    # 2. Critical chain
    print("=== Critical Chain ===")
    chain = client.analyze_critical_chain()
    for line in chain.splitlines()[:10]:
        print(f"  {line}")

    print()

    # 3. Security audit on active services
    print("=== Security Audit ===")
    active = client.list_units(unit_type="service", state="active")
    for svc in active[:5]:
        try:
            analysis = client.analyze_security(svc.name)
            print(f"  {svc.name:<35} {analysis.exposure:.1f}/10.0")
        except Exception:
            pass

    print()

    # 4. Verify all enabled service files
    print("=== Unit Verification ===")
    files = client.list_unit_files(unit_type="service", state="enabled")
    errors = 0
    for f in files:
        messages = client.analyze_verify(f.name)
        if messages:
            errors += 1
            print(f"  {f.name}: {len(messages)} issue(s)")

    if errors == 0:
        print("  All enabled services verified OK")

full_audit()
```

!!! check
    This script gives you a complete picture of boot performance, startup dependencies, security posture, and configuration validity in one run.

## CLI Commands

All analysis tools are available from the command line.

### Blame

```console
$ systemd-client analyze-blame
    32.875s  pmlogger.service
    12.456s  NetworkManager-wait-online.service
     8.234s  docker.service
```

### Security

```console
$ systemd-client analyze-security my-app.service
  my-app.service: 7.2/10.0 exposure
    [MEDIUM] PrivateTmp is not set: no
    [MEDIUM] ProtectSystem is not set: no
```

### Verify

```console
$ systemd-client analyze-verify my-app.service
  my-app.service: Unknown key name 'ExecStrat' in section 'Service'
```

A clean unit file produces:

```console
$ systemd-client analyze-verify my-app.service
my-app.service: OK
```

### JSON Output

All analysis commands support `--json` for scripting:

```console
$ systemd-client --json analyze-blame | jq '.[0:3]'
$ systemd-client --json analyze-security my-app.service | jq '.exposure'
```

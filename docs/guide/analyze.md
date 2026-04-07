# System Analysis

Boot analysis, security scoring, and unit file verification using `systemd-analyze`.

## Boot Blame

Find the slowest units at boot:

```python hl_lines="4-5"
from systemd_client import SystemdClient

with SystemdClient() as client:
    for entry in client.analyze_blame()[:10]:
        print(f"{entry.time_us / 1e6:>8.3f}s  {entry.unit}")
```

!!! check "Output"
    ```
      32.875s  pmlogger.service
       0.245s  dbus.service
       0.120s  pipewire.service
    ```

## Security Scoring

Audit the security hardening of a service. Score from 0.0 (hardened) to 10.0 (exposed):

```python hl_lines="2-3"
sec = client.analyze_security("my-app.service")
print(f"Exposure: {sec.exposure}/10.0")

for issue in sec.issues[:5]:
    print(f"  [{issue.severity}] {issue.description}: {issue.value}")
```

!!! tip
    A score below 3.0 is well-hardened. Above 7.0 needs attention.

## Verify Unit Files

Check unit file syntax before deploying:

```python
errors = client.analyze_verify("my-app.service")
if errors:
    for msg in errors:
        print(f"  {msg}")
else:
    print("Unit file OK")
```

## Critical Chain

Show the boot critical path:

```python
chain = client.analyze_critical_chain()
print(chain)
```

## CLI

```bash
systemd-client analyze-blame
systemd-client analyze-security my-app.service
systemd-client analyze-verify my-app.service
```

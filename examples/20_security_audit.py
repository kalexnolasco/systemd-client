#!/usr/bin/env python3
"""Audit security of all services.

Runs systemd-analyze security against every active service and prints
an exposure score (0 = fully hardened, 10 = wide open). Also shows
boot blame analysis for the slowest units.

Usage:
    python examples/20_security_audit.py
"""

from systemd_client import SystemdClient

client = SystemdClient()

# -- Boot blame: slowest units at startup --
print("=== Boot Blame (top 10 slowest) ===\n")

blame = client.analyze_blame()
for entry in blame[:10]:
    time_ms = entry.time_us / 1000
    print(f"  {time_ms:>8.1f}ms  {entry.unit}")

# -- Security audit for all active services --
print("\n=== Security Audit ===\n")

services = client.list_units(unit_type="service", state="active")
results = []

for svc in services:
    try:
        analysis = client.analyze_security(svc.name)
        results.append(analysis)
    except Exception as e:
        print(f"  [SKIP] {svc.name}: {e}")

# Sort by exposure score (worst first)
results.sort(key=lambda a: a.exposure, reverse=True)

print(f"  {'SERVICE':<45} {'EXPOSURE':>8}  RATING")
print("  " + "-" * 70)

for analysis in results:
    if analysis.exposure <= 2.0:
        rating = "OK"
    elif analysis.exposure <= 5.0:
        rating = "MEDIUM"
    elif analysis.exposure <= 7.5:
        rating = "EXPOSED"
    else:
        rating = "UNSAFE"

    print(f"  {analysis.unit:<45} {analysis.exposure:>8.1f}  {rating}")

# Show detailed issues for the worst offender
if results:
    worst = results[0]
    print(f"\n--- Detailed issues for {worst.unit} (exposure={worst.exposure}) ---")
    for issue in worst.issues[:10]:
        print(f"  [{issue.severity}] {issue.description}")
        if issue.value:
            print(f"           value: {issue.value}")

# systemd-client — High-Level Python Client for systemd User Services

<div align="center">

![Module](https://img.shields.io/badge/Module-systemd--client-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-0.1.0-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%20|%203.12%20|%203.13%20|%203.14-yellow?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-LGPL--2.1-orange?style=for-the-badge)
![systemd](https://img.shields.io/badge/systemd-user%20space-grey?style=for-the-badge&logo=linux&logoColor=white)

**Unified async + sync Python API for systemd unit management and journal reading**

**API unificada async + sync en Python para gestion de unidades systemd y lectura del journal**

---

### Choose Your Language / Elige tu idioma

<p align="center">
  <a href="README.en.md">
    <img src="https://img.shields.io/badge/English-Documentation-blue?style=for-the-badge&logo=markdown" alt="English Documentation" height="50">
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="README.es.md">
    <img src="https://img.shields.io/badge/Espa%C3%B1ol-Documentaci%C3%B3n-red?style=for-the-badge&logo=markdown" alt="Spanish Documentation" height="50">
  </a>
</p>

---

### Architecture Overview

```mermaid
graph TD
    subgraph APP["🐍 Your Application"]
        SYNC["SystemdClient<br/>Synchronous API"]
        ASYNC["AsyncSystemdClient<br/>Async API"]
    end

    subgraph BACKENDS["⚙️ Backends"]
        SUB["🖥️ SubprocessBackend<br/>systemctl --user"]
        DBUS["🔌 DBusBackend<br/>dasbus (optional)"]
    end

    subgraph JOURNAL["📋 Journal Reader"]
        JR["AsyncJournalReader<br/>journalctl --user --output=json"]
    end

    subgraph SYSTEMD["🐧 systemd (user session)"]
        UNITS[("🔧 User Units<br/>services, timers, sockets")]
        JRNL[("📜 Journal<br/>log entries")]
    end

    SYNC --> ASYNC
    ASYNC --> SUB
    ASYNC --> DBUS
    ASYNC --> JR
    SUB --> UNITS
    DBUS --> UNITS
    JR --> JRNL

    style APP fill:#d0ebff,stroke:#1971c2,stroke-width:2px
    style BACKENDS fill:#b2f2bb,stroke:#2f9e44,stroke-width:2px
    style JOURNAL fill:#f3d9fa,stroke:#9c36b5,stroke-width:2px
    style SYSTEMD fill:#fff3bf,stroke:#f08c00,stroke-width:2px
    style SYNC fill:#d0ebff,stroke:#1971c2,stroke-width:2px
    style ASYNC fill:#d0ebff,stroke:#1971c2,stroke-width:2px
    style SUB fill:#b2f2bb,stroke:#2f9e44,stroke-width:2px
    style DBUS fill:#b2f2bb,stroke:#2f9e44,stroke-width:2px
    style JR fill:#f3d9fa,stroke:#9c36b5,stroke-width:2px
    style UNITS fill:#fff3bf,stroke:#f08c00
    style JRNL fill:#fff3bf,stroke:#f08c00
```

### Quick Start

```bash
# Install
pip install systemd-client

# Install with DBus backend support
pip install systemd-client[dbus]

# Install with Pydantic models
pip install systemd-client[all]
```

```python
from systemd_client import SystemdClient

client = SystemdClient()
for unit in client.list_units(unit_type="service"):
    print(f"{unit.name}: {unit.active_state}")
```

---

**systemd-client** · [github.com/kalexnolasco/systemd-client](https://github.com/kalexnolasco/systemd-client)

&copy; 2026 kalexnolasco

</div>

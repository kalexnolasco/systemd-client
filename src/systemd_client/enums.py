"""StrEnum definitions for systemd states, unit types, and priorities."""

from __future__ import annotations

from enum import StrEnum


class ActiveState(StrEnum):
    """Systemd unit active states."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    RELOADING = "reloading"
    MAINTENANCE = "maintenance"


class LoadState(StrEnum):
    """Systemd unit load states."""

    LOADED = "loaded"
    NOT_FOUND = "not-found"
    BAD_SETTING = "bad-setting"
    ERROR = "error"
    MASKED = "masked"


class UnitFileState(StrEnum):
    """Systemd unit file states."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    STATIC = "static"
    MASKED = "masked"
    LINKED = "linked"
    INDIRECT = "indirect"
    GENERATED = "generated"
    TRANSIENT = "transient"
    BAD = "bad"
    ALIAS = "alias"
    ENABLED_RUNTIME = "enabled-runtime"
    LINKED_RUNTIME = "linked-runtime"
    MASKED_RUNTIME = "masked-runtime"


class SubState(StrEnum):
    """Systemd unit sub-states."""

    RUNNING = "running"
    DEAD = "dead"
    EXITED = "exited"
    FAILED = "failed"
    START_PRE = "start-pre"
    START = "start"
    START_POST = "start-post"
    STOP = "stop"
    STOP_SIGTERM = "stop-sigterm"
    STOP_SIGKILL = "stop-sigkill"
    STOP_POST = "stop-post"
    FINAL_SIGTERM = "final-sigterm"
    FINAL_SIGKILL = "final-sigkill"
    WAITING = "waiting"
    ELAPSED = "elapsed"
    MOUNTED = "mounted"
    MOUNTING = "mounting"
    UNMOUNTING = "unmounting"
    LISTENING = "listening"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PLUGGED = "plugged"
    TENTATIVE = "tentative"
    AUTO_RESTART = "auto-restart"
    CONDITION = "condition"


class UnitType(StrEnum):
    """Systemd unit types."""

    SERVICE = "service"
    SOCKET = "socket"
    TARGET = "target"
    TIMER = "timer"
    PATH = "path"
    MOUNT = "mount"
    AUTOMOUNT = "automount"
    SWAP = "swap"
    SLICE = "slice"
    SCOPE = "scope"
    DEVICE = "device"


class JournalPriority(StrEnum):
    """Journal priority levels (syslog-compatible)."""

    EMERG = "0"
    ALERT = "1"
    CRIT = "2"
    ERR = "3"
    WARNING = "4"
    NOTICE = "5"
    INFO = "6"
    DEBUG = "7"


class SystemdScope(StrEnum):
    """Systemd scope: user session or system-wide."""

    USER = "user"
    SYSTEM = "system"


class BackendType(StrEnum):
    """Available backend types for systemd communication."""

    AUTO = "auto"
    SUBPROCESS = "subprocess"
    DBUS = "dbus"

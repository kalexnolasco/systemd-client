"""Unit name <-> DBus object path escaping utilities."""

from __future__ import annotations


def unit_name_to_dbus_path(unit_name: str) -> str:
    """Convert a systemd unit name to a DBus object path component.

    Non-alphanumeric characters (except '.') are escaped as _XX hex format.
    '.' is also escaped. Leading '.' gets escaped too.

    Example: "my-app.service" -> "my_2dapp_2eservice"
    """
    parts: list[str] = []
    for char in unit_name:
        if char.isascii() and (char.isalnum() or char == "_"):
            parts.append(char)
        else:
            parts.append(f"_{ord(char):02x}")
    return "".join(parts)


def dbus_path_to_unit_name(path: str) -> str:
    """Convert a DBus object path component back to a systemd unit name.

    Reverses the _XX hex escaping.

    Example: "my_2dapp_2eservice" -> "my-app.service"
    """
    result: list[str] = []
    i = 0
    while i < len(path):
        if path[i] == "_" and i + 2 < len(path):
            hex_str = path[i + 1 : i + 3]
            try:
                result.append(chr(int(hex_str, 16)))
                i += 3
                continue
            except ValueError:
                pass
        result.append(path[i])
        i += 1
    return "".join(result)


def unescape_unit_name(name: str) -> str:
    """Decode systemd's \\xNN hex escaping in unit names.

    Example: "app-git\\x2dannex.service" -> "app-git-annex.service"
    """
    import re
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), name)


def unit_dbus_object_path(unit_name: str) -> str:
    """Return the full DBus object path for a unit.

    Example: "my-app.service" -> "/org/freedesktop/systemd1/unit/my_2dapp_2eservice"
    """
    return f"/org/freedesktop/systemd1/unit/{unit_name_to_dbus_path(unit_name)}"

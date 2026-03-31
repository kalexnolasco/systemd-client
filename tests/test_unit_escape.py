"""Tests for unit name escaping utilities."""

from systemd_client._unit_escape import (
    dbus_path_to_unit_name,
    unit_dbus_object_path,
    unit_name_to_dbus_path,
)


class TestUnitNameToDbusPath:
    def test_simple_service(self):
        assert unit_name_to_dbus_path("my-app.service") == "my_2dapp_2eservice"

    def test_alphanumeric_only(self):
        assert unit_name_to_dbus_path("myapp") == "myapp"

    def test_underscores_preserved(self):
        assert unit_name_to_dbus_path("my_app") == "my_app"

    def test_special_chars(self):
        result = unit_name_to_dbus_path("my@app.service")
        assert "_40" in result  # @ = 0x40

    def test_slash(self):
        result = unit_name_to_dbus_path("sys-fs-fuse-connections.mount")
        assert "_2d" in result


class TestDbusPathToUnitName:
    def test_roundtrip(self):
        original = "my-app.service"
        escaped = unit_name_to_dbus_path(original)
        assert dbus_path_to_unit_name(escaped) == original

    def test_roundtrip_complex(self):
        original = "my@complex-app.service"
        escaped = unit_name_to_dbus_path(original)
        assert dbus_path_to_unit_name(escaped) == original

    def test_plain_text(self):
        assert dbus_path_to_unit_name("myapp") == "myapp"


class TestUnitDbusObjectPath:
    def test_full_path(self):
        path = unit_dbus_object_path("my-app.service")
        assert path == "/org/freedesktop/systemd1/unit/my_2dapp_2eservice"

"""Tests for ServiceBuilder."""

import pytest

from systemd_client.builders import ServiceBuilder
from systemd_client.enums import UnitType
from systemd_client.exceptions import UnitFileValidationError


class TestServiceBuilderBasic:
    def test_minimal_build(self):
        unit = ServiceBuilder("my-app").exec_start("/usr/bin/app").build()
        assert unit.name == "my-app.service"
        assert unit.unit_type == UnitType.SERVICE
        assert "[Service]" in unit.content
        assert "ExecStart=/usr/bin/app" in unit.content

    def test_full_build(self):
        unit = (
            ServiceBuilder("my-app")
            .description("My Application")
            .after("network.target")
            .requires("postgresql.service")
            .type_("notify")
            .exec_start("/usr/bin/app")
            .exec_stop("/bin/kill -TERM $MAINPID")
            .exec_reload("/bin/kill -HUP $MAINPID")
            .restart("on-failure")
            .restart_sec(5)
            .user("appuser")
            .group("appgroup")
            .working_directory("/opt/app")
            .environment({"PORT": "8080", "ENV": "prod"})
            .environment_file("/opt/app/.env")
            .standard_output("journal")
            .standard_error("journal")
            .runtime_directory("my-app")
            .syslog_identifier("my-app")
            .wanted_by("default.target")
            .build()
        )
        assert "Description=My Application" in unit.content
        assert "After=network.target" in unit.content
        assert "Requires=postgresql.service" in unit.content
        assert "Type=notify" in unit.content
        assert "ExecStart=/usr/bin/app" in unit.content
        assert "ExecStop=/bin/kill -TERM $MAINPID" in unit.content
        assert "Restart=on-failure" in unit.content
        assert "RestartSec=5" in unit.content
        assert "User=appuser" in unit.content
        assert "Group=appgroup" in unit.content
        assert "WorkingDirectory=/opt/app" in unit.content
        assert 'Environment="PORT=8080" "ENV=prod"' in unit.content
        assert "EnvironmentFile=/opt/app/.env" in unit.content
        assert "WantedBy=default.target" in unit.content

    def test_template_mode(self):
        unit = (
            ServiceBuilder("my-app", template=True)
            .exec_start("/usr/bin/app --instance=%i")
            .build()
        )
        assert unit.name == "my-app@.service"
        assert "ExecStart=/usr/bin/app --instance=%i" in unit.content

    def test_fluent_chaining(self):
        b = ServiceBuilder("test")
        assert b.description("x") is b
        assert b.exec_start("/bin/x") is b
        assert b.user("x") is b
        assert b.restart("always") is b

    def test_multiple_after(self):
        unit = (
            ServiceBuilder("app")
            .exec_start("/bin/app")
            .after("network.target", "syslog.target")
            .build()
        )
        assert "After=network.target" in unit.content
        assert "After=syslog.target" in unit.content

    def test_sections_ordered(self):
        unit = (
            ServiceBuilder("app")
            .description("Test")
            .exec_start("/bin/app")
            .wanted_by("default.target")
            .build()
        )
        unit_pos = unit.content.index("[Unit]")
        service_pos = unit.content.index("[Service]")
        install_pos = unit.content.index("[Install]")
        assert unit_pos < service_pos < install_pos

    def test_empty_sections_omitted(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").build()
        assert "[Install]" not in unit.content

    def test_trailing_newline(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").build()
        assert unit.content.endswith("\n")
        assert not unit.content.endswith("\n\n")


class TestServiceBuilderSecurity:
    def test_private_tmp(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").private_tmp(True).build()
        assert "PrivateTmp=true" in unit.content

    def test_protect_system(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").protect_system("strict").build()
        assert "ProtectSystem=strict" in unit.content

    def test_dynamic_user(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").dynamic_user(True).build()
        assert "DynamicUser=true" in unit.content

    def test_remain_after_exit(self):
        unit = ServiceBuilder("app").exec_start("/bin/app").remain_after_exit(True).build()
        assert "RemainAfterExit=true" in unit.content


class TestServiceBuilderValidation:
    def test_missing_exec_start_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            ServiceBuilder("app").build()
        assert "ExecStart" in str(exc_info.value)

    def test_relative_working_directory_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            (
                ServiceBuilder("app")
                .exec_start("/bin/app")
                .working_directory("./relative")
                .build()
            )
        assert "WorkingDirectory" in str(exc_info.value)

    def test_absolute_working_directory_passes(self):
        unit = (
            ServiceBuilder("app")
            .exec_start("/bin/app")
            .working_directory("/opt/app")
            .build()
        )
        assert "WorkingDirectory=/opt/app" in unit.content

    def test_validation_error_has_builder_name(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            ServiceBuilder("my-app").build()
        assert exc_info.value.builder_name == "my-app.service"

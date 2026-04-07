"""Tests for PathBuilder."""

import pytest

from systemd_client.builders import PathBuilder
from systemd_client.enums import UnitType
from systemd_client.exceptions import UnitFileValidationError


class TestPathBuilder:
    def test_path_changed(self):
        unit = PathBuilder("watcher").path_changed("/etc/app/config.toml").build()
        assert unit.name == "watcher.path"
        assert unit.unit_type == UnitType.PATH
        assert "[Path]" in unit.content
        assert "PathChanged=/etc/app/config.toml" in unit.content

    def test_path_exists(self):
        unit = PathBuilder("watcher").path_exists("/tmp/trigger").build()
        assert "PathExists=/tmp/trigger" in unit.content

    def test_directory_not_empty(self):
        unit = PathBuilder("inbox").directory_not_empty("/var/spool/inbox").build()
        assert "DirectoryNotEmpty=/var/spool/inbox" in unit.content

    def test_full_path(self):
        unit = (
            PathBuilder("watcher")
            .description("Config watcher")
            .path_changed("/etc/app/config.toml")
            .path_modified("/etc/app/secrets.toml")
            .unit("config-reload.service")
            .make_directory(True)
            .wanted_by("default.target")
            .build()
        )
        assert "PathChanged=/etc/app/config.toml" in unit.content
        assert "PathModified=/etc/app/secrets.toml" in unit.content
        assert "Unit=config-reload.service" in unit.content
        assert "MakeDirectory=true" in unit.content

    def test_template(self):
        unit = PathBuilder("watch", template=True).path_exists("/tmp/x").build()
        assert unit.name == "watch@.path"

    def test_multiple_paths(self):
        unit = (
            PathBuilder("multi")
            .path_changed("/etc/a")
            .path_changed("/etc/b")
            .build()
        )
        assert unit.content.count("PathChanged=") == 2


class TestPathBuilderValidation:
    def test_no_path_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            PathBuilder("watcher").build()
        assert "path directive" in str(exc_info.value).lower()

    def test_relative_path_raises(self):
        with pytest.raises(UnitFileValidationError) as exc_info:
            PathBuilder("watcher").path_changed("relative/path").build()
        assert "absolute" in str(exc_info.value).lower()

    def test_glob_allows_any_path(self):
        # PathExistsGlob doesn't need to be absolute
        unit = PathBuilder("watcher").path_exists_glob("/var/log/*.log").build()
        assert "PathExistsGlob=/var/log/*.log" in unit.content

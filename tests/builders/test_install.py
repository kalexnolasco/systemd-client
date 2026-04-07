"""Tests for backend install/uninstall/edit operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.enums import SystemdScope, UnitType
from systemd_client.exceptions import UnitNotFoundError
from systemd_client.models import UnitFile


@pytest.fixture
def unit_file():
    return UnitFile(
        name="test-app.service",
        content="[Unit]\nDescription=Test\n\n[Service]\nExecStart=/bin/test\n",
        unit_type=UnitType.SERVICE,
    )


@pytest.fixture
def backend(tmp_path, monkeypatch):
    """Backend with mocked unit_file_dir and daemon_reload."""
    b = SubprocessBackend(scope=SystemdScope.USER)
    monkeypatch.setattr(
        "systemd_client.backends._subprocess.unit_file_dir",
        lambda scope: tmp_path,
    )
    b.daemon_reload = AsyncMock()
    return b


class TestInstallUnitFile:
    @pytest.mark.asyncio
    async def test_writes_file(self, backend, unit_file, tmp_path):
        path = await backend.install_unit_file(unit_file)
        written = Path(path)
        assert written.exists()
        assert written.read_text() == unit_file.content
        assert written.name == "test-app.service"

    @pytest.mark.asyncio
    async def test_calls_daemon_reload(self, backend, unit_file):
        await backend.install_unit_file(unit_file)
        backend.daemon_reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_overwrites_existing(self, backend, unit_file, tmp_path):
        (tmp_path / "test-app.service").write_text("old content")
        await backend.install_unit_file(unit_file)
        assert (tmp_path / "test-app.service").read_text() == unit_file.content

    @pytest.mark.asyncio
    async def test_creates_directory(self, backend, unit_file, tmp_path, monkeypatch):
        sub = tmp_path / "nested" / "dir"
        monkeypatch.setattr(
            "systemd_client.backends._subprocess.unit_file_dir",
            lambda scope: sub,
        )
        await backend.install_unit_file(unit_file)
        assert (sub / "test-app.service").exists()


class TestUninstallUnitFile:
    @pytest.mark.asyncio
    async def test_removes_file(self, backend, tmp_path):
        (tmp_path / "test-app.service").write_text("content")
        await backend.uninstall_unit_file("test-app.service")
        assert not (tmp_path / "test-app.service").exists()

    @pytest.mark.asyncio
    async def test_removes_dropin_dir(self, backend, tmp_path):
        (tmp_path / "test-app.service").write_text("content")
        dropin = tmp_path / "test-app.service.d"
        dropin.mkdir()
        (dropin / "override.conf").write_text("[Service]\nRestart=always\n")
        await backend.uninstall_unit_file("test-app.service")
        assert not dropin.exists()

    @pytest.mark.asyncio
    async def test_not_found_raises(self, backend):
        with pytest.raises(UnitNotFoundError):
            await backend.uninstall_unit_file("nonexistent.service")

    @pytest.mark.asyncio
    async def test_calls_daemon_reload(self, backend, tmp_path):
        (tmp_path / "test-app.service").write_text("content")
        await backend.uninstall_unit_file("test-app.service")
        backend.daemon_reload.assert_called_once()


class TestEditUnitFile:
    @pytest.mark.asyncio
    async def test_creates_dropin(self, backend, tmp_path):
        overrides = {"Service": {"Restart": "always", "RestartSec": "10"}}
        path = await backend.edit_unit_file("test-app.service", overrides)
        written = Path(path)
        assert written.exists()
        content = written.read_text()
        assert "[Service]" in content
        assert "Restart=always" in content
        assert "RestartSec=10" in content

    @pytest.mark.asyncio
    async def test_dropin_directory_name(self, backend, tmp_path):
        await backend.edit_unit_file(
            "test-app.service", {"Service": {"Restart": "always"}},
        )
        assert (tmp_path / "test-app.service.d").is_dir()
        assert (tmp_path / "test-app.service.d" / "override.conf").exists()

    @pytest.mark.asyncio
    async def test_calls_daemon_reload(self, backend, tmp_path):
        await backend.edit_unit_file(
            "test-app.service", {"Service": {"Restart": "always"}},
        )
        backend.daemon_reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_sections(self, backend, tmp_path):
        overrides = {
            "Unit": {"Description": "Updated"},
            "Service": {"Restart": "always"},
        }
        path = await backend.edit_unit_file("test-app.service", overrides)
        content = Path(path).read_text()
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "Description=Updated" in content

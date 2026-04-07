"""Tests for CLI app."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from systemd_client.cli._app import main
from systemd_client.enums import ActiveState, LoadState, SubState, UnitFileState
from systemd_client.models import EnableResult, UnitFileInfo, UnitInfo, UnitStatus


@pytest.fixture
def mock_client():
    """Mock SystemdClient for CLI tests."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.list_units.return_value = [
        UnitInfo(
            "test.service", "Test Service",
            LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING,
        ),
    ]
    client.list_unit_files.return_value = [
        UnitFileInfo("test.service", UnitFileState.ENABLED, preset="enabled"),
        UnitFileInfo("other.service", UnitFileState.DISABLED, preset="disabled"),
    ]
    client.status.return_value = UnitStatus(
        name="test.service",
        description="Test Service",
        load_state=LoadState.LOADED,
        active_state=ActiveState.ACTIVE,
        sub_state=SubState.RUNNING,
    )
    client.cat.return_value = "[Unit]\nDescription=Test\n"
    client.enable.return_value = EnableResult()
    client.disable.return_value = EnableResult()
    client.mask.return_value = EnableResult()
    client.unmask.return_value = EnableResult()
    client.journal.return_value = []
    return client


class TestCLIList:
    def test_list(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["list"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "test.service" in captured.out

    def test_list_json(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["--json", "list"])
        assert ret == 0
        captured = capsys.readouterr()
        assert '"name"' in captured.out


class TestCLIListUnitFiles:
    def test_list_unit_files(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["list-unit-files"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "test.service" in captured.out

    def test_list_unit_files_json(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["--json", "list-unit-files"])
        assert ret == 0
        captured = capsys.readouterr()
        assert '"name"' in captured.out


class TestCLIStatus:
    def test_status(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["status", "test.service"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "test.service" in captured.out


class TestCLICat:
    def test_cat(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["cat", "test.service"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "[Unit]" in captured.out


class TestCLIUnitOps:
    @pytest.mark.parametrize("cmd", ["start", "stop", "restart", "reload"])
    def test_unit_ops(self, mock_client, capsys, cmd):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main([cmd, "test.service"])
        assert ret == 0
        getattr(mock_client, cmd).assert_called_once_with("test.service", no_block=False)

    @pytest.mark.parametrize("cmd", ["start", "stop", "restart"])
    def test_batch_ops(self, mock_client, capsys, cmd):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main([cmd, "a.service", "b.service"])
        assert ret == 0
        batch_method = f"{cmd}_units"
        getattr(mock_client, batch_method).assert_called_once()

    def test_no_block(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["start", "--no-block", "test.service"])
        assert ret == 0
        mock_client.start.assert_called_once_with("test.service", no_block=True)

    def test_try_restart(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["try-restart", "test.service"])
        assert ret == 0
        mock_client.try_restart.assert_called_once()

    def test_reload_or_restart(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["reload-or-restart", "test.service"])
        assert ret == 0
        mock_client.reload_or_restart.assert_called_once()

    @pytest.mark.parametrize("cmd", ["enable", "disable", "mask", "unmask"])
    def test_enable_ops(self, mock_client, capsys, cmd):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main([cmd, "test.service"])
        assert ret == 0


class TestCLIDaemonReload:
    def test_daemon_reload(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["daemon-reload"])
        assert ret == 0
        mock_client.daemon_reload.assert_called_once()


class TestCLIResetFailed:
    def test_reset_failed_unit(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["reset-failed", "test.service"])
        assert ret == 0
        mock_client.reset_failed.assert_called_once_with("test.service")

    def test_reset_failed_all(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["reset-failed"])
        assert ret == 0
        mock_client.reset_failed.assert_called_once_with(None)


class TestCLIScope:
    def test_system_scope(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["--scope", "system", "list"])
        assert ret == 0


class TestCLIJournal:
    def test_journal(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["journal", "--unit", "test.service", "--lines", "10"])
        assert ret == 0


class TestCLIVersion:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

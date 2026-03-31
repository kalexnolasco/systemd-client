"""Tests for CLI app."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from systemd_client.cli._app import main
from systemd_client.enums import ActiveState, LoadState, SubState
from systemd_client.models import EnableResult, UnitInfo, UnitStatus


@pytest.fixture
def mock_client():
    """Mock SystemdClient for CLI tests."""
    client = MagicMock()
    client.list_units.return_value = [
        UnitInfo(
            "test.service", "Test Service",
            LoadState.LOADED, ActiveState.ACTIVE, SubState.RUNNING,
        ),
    ]
    client.status.return_value = UnitStatus(
        name="test.service",
        description="Test Service",
        load_state=LoadState.LOADED,
        active_state=ActiveState.ACTIVE,
        sub_state=SubState.RUNNING,
    )
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


class TestCLIStatus:
    def test_status(self, mock_client, capsys):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main(["status", "test.service"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "test.service" in captured.out


class TestCLIUnitOps:
    @pytest.mark.parametrize("cmd", ["start", "stop", "restart", "reload"])
    def test_unit_ops(self, mock_client, capsys, cmd):
        with patch("systemd_client.cli._app.SystemdClient", return_value=mock_client):
            ret = main([cmd, "test.service"])
        assert ret == 0
        getattr(mock_client, cmd).assert_called_once_with("test.service")

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

"""Tests for environment and session management."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from systemd_client.backends._subprocess import SubprocessBackend
from systemd_client.client import AsyncSystemdClient, SystemdClient
from systemd_client.enums import BackendType
from systemd_client.models import SessionInfo, UserInfo


@pytest.fixture
def backend():
    return SubprocessBackend()


@pytest.fixture
def mock_systemctl(monkeypatch):
    def _factory(stdout: str = "", stderr: str = "", returncode: int = 0):
        mock = AsyncMock(return_value=(stdout, stderr, returncode))
        monkeypatch.setattr(SubprocessBackend, "_run_systemctl", mock)
        return mock
    return _factory


@pytest.fixture
def mock_loginctl(monkeypatch):
    def _factory(stdout: str = ""):
        mock = AsyncMock(return_value=stdout)
        monkeypatch.setattr(SubprocessBackend, "_run_loginctl", mock)
        return mock
    return _factory


class TestShowEnvironment:
    @pytest.mark.asyncio
    async def test_parses_env(self, backend, mock_systemctl):
        mock_systemctl(stdout="HOME=/home/user\nPATH=/usr/bin\nLANG=en_US.UTF-8\n")
        env = await backend.show_environment()
        assert env["HOME"] == "/home/user"
        assert env["PATH"] == "/usr/bin"
        assert len(env) == 3


class TestSetEnvironment:
    @pytest.mark.asyncio
    async def test_sets_vars(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.set_environment({"MY_VAR": "hello", "OTHER": "world"})
        call_args = mock.call_args[0]
        assert "set-environment" in call_args
        assert "MY_VAR=hello" in call_args


class TestUnsetEnvironment:
    @pytest.mark.asyncio
    async def test_unsets_vars(self, backend, mock_systemctl):
        mock = mock_systemctl()
        await backend.unset_environment(["MY_VAR", "OTHER"])
        call_args = mock.call_args[0]
        assert "unset-environment" in call_args
        assert "MY_VAR" in call_args


class TestListSessions:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_loginctl):
        data = [
            {"session": "3", "uid": 1000, "user": "testuser", "seat": "seat0", "tty": "tty2"},
        ]
        mock_loginctl(stdout=json.dumps(data))
        sessions = await backend.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == "3"
        assert sessions[0].user == "testuser"
        assert sessions[0].uid == 1000

    @pytest.mark.asyncio
    async def test_empty(self, backend, mock_loginctl):
        mock_loginctl(stdout="[]")
        assert await backend.list_sessions() == []


class TestListUsers:
    @pytest.mark.asyncio
    async def test_parses_json(self, backend, mock_loginctl):
        data = [{"uid": 1000, "user": "testuser", "state": "active"}]
        mock_loginctl(stdout=json.dumps(data))
        users = await backend.list_users()
        assert len(users) == 1
        assert users[0].name == "testuser"
        assert users[0].uid == 1000


class TestSessionModels:
    def test_session_info(self):
        s = SessionInfo(id="3", uid=1000, user="test", seat="seat0")
        assert s.id == "3"
        assert s.seat == "seat0"

    def test_user_info(self):
        u = UserInfo(uid=1000, name="test", state="active")
        assert u.name == "test"

    def test_frozen(self):
        s = SessionInfo(id="1", uid=0, user="root")
        with pytest.raises(AttributeError):
            s.user = "other"  # type: ignore[misc]


class TestClientEnvMethods:
    @pytest.fixture
    def mock_backend(self):
        backend = AsyncMock()
        backend.show_environment = AsyncMock(return_value={"HOME": "/home/test"})
        backend.set_environment = AsyncMock()
        backend.unset_environment = AsyncMock()
        backend.list_sessions = AsyncMock(return_value=[])
        backend.list_users = AsyncMock(return_value=[])
        backend.terminate_session = AsyncMock()
        backend.lock_session = AsyncMock()
        backend.close = AsyncMock()
        return backend

    @pytest.mark.asyncio
    async def test_show_environment(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        env = await client.show_environment()
        assert env["HOME"] == "/home/test"

    @pytest.mark.asyncio
    async def test_set_environment(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        await client.set_environment({"X": "1"})
        mock_backend.set_environment.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sessions(self, mock_backend):
        client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
        client._backend = mock_backend
        assert await client.list_sessions() == []

    def test_sync_show_environment(self, mock_backend):
        with patch("systemd_client.client.get_backend", return_value=mock_backend):
            client = SystemdClient(backend=BackendType.SUBPROCESS)
            client._async_client._backend = mock_backend
            env = client.show_environment()
            assert env["HOME"] == "/home/test"

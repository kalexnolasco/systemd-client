"""Tests for systemd-analyze module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from systemd_client._analyze import (
    analyze_blame,
    analyze_critical_chain,
    analyze_security,
    analyze_verify,
)
from systemd_client.client import AsyncSystemdClient
from systemd_client.enums import BackendType, SystemdScope
from systemd_client.models import BlameEntry, SecurityAnalysis, SecurityIssue


@pytest.fixture
def mock_run_analyze():
    """Mock _run_analyze to avoid subprocess calls."""
    with patch("systemd_client._analyze._run_analyze") as mock:
        yield mock


class TestAnalyzeBlame:
    @pytest.mark.asyncio
    async def test_parses_blame(self, mock_run_analyze):
        mock_run_analyze.return_value = (
            "  32.875s  pmlogger.service\n"
            "   245ms  dbus.service\n"
            "   100us  test.service\n"
        )
        entries = await analyze_blame(SystemdScope.USER)
        assert len(entries) == 3
        assert entries[0].unit == "pmlogger.service"
        assert entries[0].time_us == 32_875_000
        assert entries[1].time_us == 245_000
        assert entries[2].time_us == 100

    @pytest.mark.asyncio
    async def test_empty(self, mock_run_analyze):
        mock_run_analyze.return_value = ""
        entries = await analyze_blame(SystemdScope.USER)
        assert entries == []


class TestAnalyzeCriticalChain:
    @pytest.mark.asyncio
    async def test_returns_raw(self, mock_run_analyze):
        mock_run_analyze.return_value = (
            "multi-user.target @5.123s\n└─dbus.service @1.234s +0.100s\n"
        )
        result = await analyze_critical_chain(SystemdScope.USER)
        assert "multi-user.target" in result

    @pytest.mark.asyncio
    async def test_with_unit(self, mock_run_analyze):
        mock_run_analyze.return_value = "test.service @1.0s\n"
        await analyze_critical_chain(SystemdScope.USER, "test.service")
        call_args = mock_run_analyze.call_args[0]
        assert "test.service" in call_args


class TestAnalyzeSecurity:
    @pytest.mark.asyncio
    async def test_parses_json(self, mock_run_analyze):
        data = [{
            "unit": "test.service",
            "exposure": 5.5,
            "predicates": [
                {
                    "set_name": "PrivateTmp",
                    "description": "Service runs with private /tmp",
                    "badness_description": "unsafe",
                    "value": "no",
                },
            ],
        }]
        mock_run_analyze.return_value = json.dumps(data)
        result = await analyze_security(SystemdScope.USER, "test.service")
        assert result.unit == "test.service"
        assert result.exposure == 5.5
        assert len(result.issues) == 1
        assert result.issues[0].id == "PrivateTmp"

    @pytest.mark.asyncio
    async def test_not_found(self, mock_run_analyze):
        mock_run_analyze.return_value = "[]"
        result = await analyze_security(SystemdScope.USER, "missing.service")
        assert result.exposure == 10.0


class TestAnalyzeVerify:
    @pytest.mark.asyncio
    async def test_clean(self, mock_run_analyze):
        mock_run_analyze.return_value = ""
        msgs = await analyze_verify(SystemdScope.USER, "test.service")
        assert msgs == []


class TestAnalyzeModels:
    def test_blame_entry(self):
        e = BlameEntry(time_us=1_000_000, unit="test.service")
        assert e.time_us == 1_000_000

    def test_security_issue(self):
        i = SecurityIssue(id="PrivateTmp", description="test", severity="unsafe", value="no")
        assert i.id == "PrivateTmp"

    def test_security_analysis(self):
        a = SecurityAnalysis(unit="test.service", exposure=3.5, issues=[])
        assert a.exposure == 3.5

    def test_frozen(self):
        e = BlameEntry(time_us=0, unit="x")
        with pytest.raises(AttributeError):
            e.unit = "y"  # type: ignore[misc]


class TestClientAnalyzeMethods:
    @pytest.mark.asyncio
    async def test_async_blame(self):
        with patch("systemd_client._analyze.analyze_blame", new_callable=AsyncMock) as mock:
            mock.return_value = [BlameEntry(1000, "test.service")]
            client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
            entries = await client.analyze_blame()
            assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_async_security(self):
        with patch("systemd_client._analyze.analyze_security", new_callable=AsyncMock) as mock:
            mock.return_value = SecurityAnalysis("test.service", 3.0)
            client = AsyncSystemdClient(backend=BackendType.SUBPROCESS)
            result = await client.analyze_security("test.service")
            assert result.exposure == 3.0

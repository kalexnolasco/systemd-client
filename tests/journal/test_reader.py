"""Tests for journal reader."""

from __future__ import annotations

import pytest

from systemd_client.journal._query import JournalQuery
from systemd_client.journal._reader import AsyncJournalReader


@pytest.fixture
def reader():
    return AsyncJournalReader()


class TestAsyncJournalReaderQuery:
    @pytest.mark.asyncio
    async def test_query_parses_output(
        self, reader, mock_subprocess_run, sample_journal_json_lines,
    ):
        stdout = "\n".join(sample_journal_json_lines)
        _mock_create, _mock_proc = mock_subprocess_run(stdout=stdout)

        q = JournalQuery(unit="test-app.service", lines=10)
        entries = await reader.query(q)

        assert len(entries) == 2
        assert entries[0].message == "Application started"
        assert entries[1].message == "Warning: low memory"

    @pytest.mark.asyncio
    async def test_query_empty_output(self, reader, mock_subprocess_run):
        mock_subprocess_run(stdout="")
        q = JournalQuery(lines=10)
        entries = await reader.query(q)
        assert entries == []

    @pytest.mark.asyncio
    async def test_query_skips_bad_lines(self, reader, mock_subprocess_run):
        stdout = '{"MESSAGE": "good"}\nnot json\n{"MESSAGE": "also good"}'
        mock_subprocess_run(stdout=stdout)
        q = JournalQuery(lines=10)
        entries = await reader.query(q)
        assert len(entries) == 2

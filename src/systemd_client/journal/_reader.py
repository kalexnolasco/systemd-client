"""Async and sync journal readers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from systemd_client._sync import run_sync, sync_generator_bridge
from systemd_client.exceptions import JournalError, SubprocessError
from systemd_client.journal._parser import parse_journal_line
from systemd_client.journal._query import JournalQuery

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from systemd_client.models import JournalEntry


class AsyncJournalReader:
    """Async journal reader using journalctl subprocess."""

    async def query(self, q: JournalQuery) -> list[JournalEntry]:
        """Run a journal query and return all matching entries."""
        args = q.to_args()
        cmd = ["journalctl", *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode and proc.returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            raise SubprocessError(cmd, proc.returncode, stderr)

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        entries: list[JournalEntry] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(parse_journal_line(line))
            except JournalError:
                continue
        return entries

    async def follow(self, q: JournalQuery) -> AsyncIterator[JournalEntry]:
        """Follow journal output as an async generator."""
        follow_query = JournalQuery(
            unit=q.unit,
            lines=q.lines,
            since=q.since,
            until=q.until,
            priority=q.priority,
            grep=q.grep,
            boot=q.boot,
            reverse=False,
            follow=True,
            identifiers=q.identifiers,
        )
        args = follow_query.to_args()
        cmd = ["journalctl", *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    yield parse_journal_line(line)
                except JournalError:
                    continue
        finally:
            proc.terminate()
            await proc.wait()


class JournalReader:
    """Synchronous journal reader wrapping AsyncJournalReader."""

    def __init__(self) -> None:
        self._async_reader = AsyncJournalReader()

    def query(self, q: JournalQuery) -> list[JournalEntry]:
        """Run a journal query and return all matching entries."""
        return run_sync(self._async_reader.query(q))  # type: ignore[return-value]

    def follow(self, q: JournalQuery) -> Iterator[JournalEntry]:
        """Follow journal output as a synchronous iterator."""
        return sync_generator_bridge(lambda: self._async_reader.follow(q))

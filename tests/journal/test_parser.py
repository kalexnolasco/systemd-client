"""Tests for journal parser."""

import json

import pytest

from systemd_client.enums import JournalPriority
from systemd_client.exceptions import JournalParseError
from systemd_client.journal._parser import parse_journal_line


class TestParseJournalLine:
    def test_basic_entry(self):
        data = {
            "MESSAGE": "Hello world",
            "PRIORITY": "6",
            "__REALTIME_TIMESTAMP": "1700000000000000",
            "_SYSTEMD_UNIT": "test.service",
            "SYSLOG_IDENTIFIER": "test",
            "_PID": "1234",
            "_HOSTNAME": "myhost",
            "__CURSOR": "s=abc",
        }
        entry = parse_journal_line(json.dumps(data))
        assert entry.message == "Hello world"
        assert entry.priority == JournalPriority.INFO
        assert entry.timestamp is not None
        assert entry.unit == "test.service"
        assert entry.pid == 1234
        assert entry.hostname == "myhost"
        assert entry.cursor == "s=abc"

    def test_minimal_entry(self):
        data = {"MESSAGE": "test"}
        entry = parse_journal_line(json.dumps(data))
        assert entry.message == "test"
        assert entry.priority == JournalPriority.INFO
        assert entry.timestamp is None

    def test_unknown_priority_defaults_to_info(self):
        data = {"MESSAGE": "test", "PRIORITY": "99"}
        entry = parse_journal_line(json.dumps(data))
        assert entry.priority == JournalPriority.INFO

    def test_extra_fields(self):
        data = {
            "MESSAGE": "test",
            "PRIORITY": "6",
            "CUSTOM_FIELD": "custom_value",
        }
        entry = parse_journal_line(json.dumps(data))
        assert entry.fields["CUSTOM_FIELD"] == "custom_value"

    def test_invalid_json_raises(self):
        with pytest.raises(JournalParseError):
            parse_journal_line("not json at all")

    def test_monotonic_timestamp(self):
        data = {
            "MESSAGE": "test",
            "PRIORITY": "6",
            "__MONOTONIC_TIMESTAMP": "123456789",
        }
        entry = parse_journal_line(json.dumps(data))
        assert entry.monotonic_timestamp == 123456789

"""Tests for JournalQuery."""

from systemd_client.enums import JournalPriority, SystemdScope
from systemd_client.journal._query import JournalQuery


class TestJournalQuery:
    def test_default_args(self):
        q = JournalQuery()
        args = q.to_args()
        assert "--user" in args
        assert "--output=json" in args
        assert "--no-pager" in args

    def test_system_scope(self):
        q = JournalQuery(scope=SystemdScope.SYSTEM)
        args = q.to_args()
        assert "--system" in args
        assert "--user" not in args

    def test_user_scope(self):
        q = JournalQuery(scope=SystemdScope.USER)
        args = q.to_args()
        assert "--user" in args
        assert "--system" not in args

    def test_unit_filter(self):
        q = JournalQuery(unit="test.service")
        args = q.to_args()
        assert "--unit" in args
        idx = args.index("--unit")
        assert args[idx + 1] == "test.service"

    def test_lines(self):
        q = JournalQuery(lines=50)
        args = q.to_args()
        assert "--lines" in args
        assert "50" in args

    def test_since_until(self):
        q = JournalQuery(since="1h ago", until="now")
        args = q.to_args()
        assert "--since" in args
        assert "--until" in args

    def test_priority(self):
        q = JournalQuery(priority=JournalPriority.WARNING)
        args = q.to_args()
        assert "--priority" in args
        assert "4" in args

    def test_grep(self):
        q = JournalQuery(grep="error.*timeout")
        args = q.to_args()
        assert "--grep" in args
        assert "error.*timeout" in args

    def test_follow(self):
        q = JournalQuery(follow=True)
        args = q.to_args()
        assert "--follow" in args

    def test_reverse(self):
        q = JournalQuery(reverse=True)
        args = q.to_args()
        assert "--reverse" in args

    def test_identifiers(self):
        q = JournalQuery(identifiers=["sshd", "nginx"])
        args = q.to_args()
        assert args.count("--identifier") == 2

    def test_combined(self):
        q = JournalQuery(
            unit="test.service",
            lines=100,
            priority=JournalPriority.ERR,
            reverse=True,
        )
        args = q.to_args()
        assert "--unit" in args
        assert "--lines" in args
        assert "--priority" in args
        assert "--reverse" in args

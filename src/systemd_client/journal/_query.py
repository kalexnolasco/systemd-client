"""JournalQuery dataclass and argument builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systemd_client.enums import JournalPriority, SystemdScope


@dataclass(frozen=True, slots=True)
class JournalQuery:
    """Parameters for querying the journal."""

    unit: str | None = None
    lines: int | None = None
    since: str | None = None
    until: str | None = None
    priority: JournalPriority | None = None
    grep: str | None = None
    boot: str | None = None
    reverse: bool = False
    follow: bool = False
    identifiers: list[str] = field(default_factory=list)
    scope: SystemdScope | None = None

    def to_args(self) -> list[str]:
        """Build journalctl command-line arguments from this query."""
        args: list[str] = ["--output=json", "--no-pager"]

        # Scope flag: --user or --system (system is journalctl default)
        if self.scope is not None:
            args.append(f"--{self.scope.value}")
        else:
            args.append("--user")

        if self.unit:
            args.extend(["--unit", self.unit])
        if self.lines is not None:
            args.extend(["--lines", str(self.lines)])
        if self.since:
            args.extend(["--since", self.since])
        if self.until:
            args.extend(["--until", self.until])
        if self.priority is not None:
            args.extend(["--priority", self.priority.value])
        if self.grep:
            args.extend(["--grep", self.grep])
        if self.boot is not None:
            args.extend(["--boot", self.boot])
        if self.reverse:
            args.append("--reverse")
        if self.follow:
            args.append("--follow")
        for ident in self.identifiers:
            args.extend(["--identifier", ident])

        return args

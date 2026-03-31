# Journal Reader

systemd-client provides both high-level journal access through the client and low-level access through `JournalReader` / `AsyncJournalReader`.

!!! note
    The journal **always** uses subprocess (`journalctl --user --output=json`) regardless of the backend setting. This is because systemd's journal has no D-Bus API.

## Through the Client

The simplest way to access the journal:

```python
from systemd_client import SystemdClient, JournalPriority

client = SystemdClient()

# Basic query
entries = client.journal("my-app.service", lines=50)

# With all filters
entries = client.journal(
    unit="my-app.service",
    lines=100,
    since="1h ago",
    until="30m ago",
    priority=JournalPriority.WARNING,
    grep="error|timeout",
)
```

## Low-Level JournalReader

For more control, use `JournalReader` and `JournalQuery` directly:

```python
from systemd_client import JournalReader, JournalPriority
from systemd_client.journal import JournalQuery

reader = JournalReader()

query = JournalQuery(
    unit="my-app.service",
    priority=JournalPriority.ERR,
    lines=50,
    since="2h ago",
    reverse=True,
    identifiers=["my-app"],
)

entries = reader.query(query)
```

### JournalQuery Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `unit` | `str \| None` | Filter by unit name |
| `lines` | `int \| None` | Number of recent entries |
| `since` | `str \| None` | Start time (`"1h ago"`, `"2024-01-01"`, `"today"`) |
| `until` | `str \| None` | End time |
| `priority` | `JournalPriority \| None` | Minimum priority level |
| `grep` | `str \| None` | Regex filter on message content |
| `boot` | `str \| None` | Filter by boot ID |
| `reverse` | `bool` | Newest entries first |
| `follow` | `bool` | Follow new entries (used internally) |
| `identifiers` | `list[str]` | Filter by syslog identifiers |

### Inspecting the generated command

```python
query = JournalQuery(unit="my-app.service", lines=50, priority=JournalPriority.WARNING)
print(query.to_args())
# ['--user', '--output=json', '--no-pager', '--unit', 'my-app.service',
#  '--lines', '50', '--priority', '4']
```

## Following the Journal

### Sync (blocking iterator)

```python
for entry in client.journal_follow("my-app.service"):
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"{ts} [{entry.priority.name}] {entry.message}")
```

### Async (non-blocking generator)

```python
async for entry in async_client.journal_follow("my-app.service"):
    print(entry.message)
```

### Low-level follow

```python
reader = JournalReader()
query = JournalQuery(unit="my-app.service", lines=10)

for entry in reader.follow(query):
    print(entry.message)
```

## JournalEntry Fields

Each entry is a frozen dataclass:

```python
entry.message              # str: log message
entry.priority             # JournalPriority: emerg(0)..debug(7)
entry.timestamp            # datetime | None: wall-clock UTC
entry.monotonic_timestamp  # int | None: microseconds
entry.unit                 # str | None: originating unit
entry.syslog_identifier    # str | None: program name
entry.pid                  # int | None: process ID
entry.uid                  # int | None: user ID
entry.boot_id              # str | None: boot identifier
entry.hostname             # str | None: machine hostname
entry.cursor               # str | None: journal cursor
entry.fields               # dict[str, str]: all extra fields
```

### Accessing extra fields

```python
entries = client.journal("my-app.service", lines=10)
for entry in entries:
    # Standard fields
    print(entry.message, entry.pid)

    # Extra journal fields
    cgroup = entry.fields.get("_SYSTEMD_CGROUP", "")
    exe = entry.fields.get("_EXE", "")
```

## Priority Levels

```python
from systemd_client import JournalPriority

JournalPriority.EMERG    # "0" — system is unusable
JournalPriority.ALERT    # "1" — immediate action needed
JournalPriority.CRIT     # "2" — critical conditions
JournalPriority.ERR      # "3" — error conditions
JournalPriority.WARNING  # "4" — warning conditions
JournalPriority.NOTICE   # "5" — normal but significant
JournalPriority.INFO     # "6" — informational
JournalPriority.DEBUG    # "7" — debug messages
```

When you pass `priority=JournalPriority.WARNING`, you get entries with priority **4 and below** (WARNING, ERR, CRIT, ALERT, EMERG).

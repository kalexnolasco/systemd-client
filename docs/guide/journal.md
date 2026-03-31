# Journal Reader

systemd-client gives you full access to the **systemd journal** -- both through the high-level client and through a dedicated low-level `JournalReader`.

Let's explore both approaches.

!!! note
    The journal **always** uses subprocess (`journalctl --user --output=json`) regardless of the backend setting. This is because systemd's journal has no D-Bus API. See [Backends](backends.md) for more details.

## Through the Client (The Easy Way)

The simplest way to read journal entries is right from your client instance:

```python hl_lines="4 7 8 9 10 11 12"
from systemd_client import SystemdClient, JournalPriority

client = SystemdClient()
entries = client.journal("my-app.service", lines=50)  # (1)!

# With all filters
entries = client.journal(
    unit="my-app.service",
    lines=100,
    since="1h ago",  # (2)!
    until="30m ago",
    priority=JournalPriority.WARNING,  # (3)!
    grep="error|timeout",  # (4)!
)
```

1. Fetches the last 50 journal entries for this unit.
2. Accepts human-readable time expressions like `"1h ago"`, `"today"`, or absolute dates like `"2025-01-15"`.
3. Filters to WARNING level **and below** (WARNING, ERR, CRIT, ALERT, EMERG). Lower number = higher severity.
4. Regex pattern applied to the message content, just like `journalctl --grep`.

!!! tip
    For most use cases, the client-level `journal()` method is all you need. Only reach for `JournalReader` when you need fine-grained control.

## Low-Level JournalReader

When you need more control -- like specifying syslog identifiers or reverse ordering -- use `JournalReader` and `JournalQuery` directly:

```python hl_lines="4 6 7 8 9 10 11 12 13 15"
from systemd_client import JournalReader, JournalPriority
from systemd_client.journal import JournalQuery

reader = JournalReader()

query = JournalQuery(
    unit="my-app.service",
    priority=JournalPriority.ERR,
    lines=50,
    since="2h ago",
    reverse=True,  # (1)!
    identifiers=["my-app"],  # (2)!
)

entries = reader.query(query)
```

1. Newest entries first -- handy when you want to see the most recent errors.
2. Filter by syslog identifier (the program name that produced the log line).

### JournalQuery Parameters

Here's every parameter you can use to build a query:

| Parameter | Type | Description |
|-----------|------|-------------|
| `unit` | `str | None` | Filter by unit name |
| `lines` | `int | None` | Number of recent entries to return |
| `since` | `str | None` | Start time (`"1h ago"`, `"2025-01-01"`, `"today"`) |
| `until` | `str | None` | End time |
| `priority` | `JournalPriority | None` | Minimum priority level |
| `grep` | `str | None` | Regex filter on message content |
| `boot` | `str | None` | Filter by boot ID |
| `reverse` | `bool` | Newest entries first (default `False`) |
| `follow` | `bool` | Follow new entries in real-time (used internally) |
| `identifiers` | `list[str]` | Filter by syslog identifiers |

### Inspect the Generated Command

Curious what `journalctl` command will actually run? You can peek at the arguments:

```python hl_lines="3"
query = JournalQuery(
    unit="my-app.service", lines=50, priority=JournalPriority.WARNING
)
print(query.to_args())
```

```console
$ python inspect_query.py
['--user', '--output=json', '--no-pager', '--unit', 'my-app.service', '--lines', '50', '--priority', '4']
```

??? info "Technical Details"
    The `to_args()` method returns the exact argument list passed to `journalctl`. This is useful for debugging when your query isn't returning the results you expect.

## Following the Journal

Real-time log tailing is supported in both sync and async flavors.

### Sync (Blocking Iterator)

```python hl_lines="1 2 3"
for entry in client.journal_follow("my-app.service"):  # (1)!
    ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
    print(f"{ts} [{entry.priority.name}] {entry.message}")
```

1. This blocks forever, yielding new entries as they appear. Press Ctrl+C to stop.

!!! warning
    The sync `journal_follow` is a **blocking** call. It will hold up your entire thread. For non-blocking follow, use the [async client](async-client.md).

### Async (Non-Blocking Generator)

```python hl_lines="1 2"
async for entry in async_client.journal_follow("my-app.service"):  # (1)!
    print(entry.message)
```

1. Non-blocking -- your event loop stays free to handle other work while waiting for new log lines.

### Low-Level Follow

You can also follow using the `JournalReader` directly:

```python hl_lines="4"
reader = JournalReader()
query = JournalQuery(unit="my-app.service", lines=10)

for entry in reader.follow(query):  # (1)!
    print(entry.message)
```

1. Starts by replaying the last 10 entries, then follows new ones in real-time.

## JournalEntry Fields

Each entry is a **frozen dataclass** with these fields:

```python hl_lines="1 2 3 4 5"
entry.message              # str: the log message  # (1)!
entry.priority             # JournalPriority: emerg(0)..debug(7)  # (2)!
entry.timestamp            # datetime | None: wall-clock UTC
entry.monotonic_timestamp  # int | None: microseconds since boot
entry.unit                 # str | None: originating unit
entry.syslog_identifier    # str | None: program name
entry.pid                  # int | None: process ID
entry.uid                  # int | None: user ID
entry.boot_id              # str | None: boot identifier
entry.hostname             # str | None: machine hostname
entry.cursor               # str | None: journal cursor  # (3)!
entry.fields               # dict[str, str]: all extra fields
```

1. The main log line content -- this is what you'll use most often.
2. `JournalPriority` is a `StrEnum`, so you can compare it as a string or use `.name` / `.value`.
3. The cursor is a unique, opaque string that identifies this exact position in the journal. Useful for bookmarking.

### Accessing Extra Fields

The `fields` dict contains **every** journal field, including internal ones that don't have named attributes:

```python hl_lines="5 6"
entries = client.journal("my-app.service", lines=10)
for entry in entries:
    print(entry.message, entry.pid)

    # Extra journal fields not on the dataclass
    cgroup = entry.fields.get("_SYSTEMD_CGROUP", "")  # (1)!
    exe = entry.fields.get("_EXE", "")
```

1. Journal fields prefixed with `_` are **trusted fields** set by the journal itself (not the logging process).

## Priority Levels

The `JournalPriority` enum follows standard syslog priority levels:

```python hl_lines="4 5"
from systemd_client import JournalPriority

JournalPriority.EMERG    # "0" -- system is unusable
JournalPriority.ALERT    # "1" -- immediate action needed
JournalPriority.CRIT     # "2" -- critical conditions
JournalPriority.ERR      # "3" -- error conditions  # (1)!
JournalPriority.WARNING  # "4" -- warning conditions
JournalPriority.NOTICE   # "5" -- normal but significant
JournalPriority.INFO     # "6" -- informational
JournalPriority.DEBUG    # "7" -- debug messages
```

1. `ERR` (not `ERROR`) follows the syslog convention.

!!! info
    When you pass `priority=JournalPriority.WARNING` to a query, you get entries at priority **4 and below** -- that means WARNING, ERR, CRIT, ALERT, and EMERG. Lower number = higher severity. This matches how `journalctl --priority` works.

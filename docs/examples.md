# Examples

Ready-to-use scripts in the [`examples/`](https://github.com/kalexnolasco/systemd-client/tree/main/examples) directory.

## Unit Management

| Script | Description |
|--------|-------------|
| `01_list_services.py` | List all user services |
| `02_service_status.py` | Get detailed service status |
| `03_start_stop_restart.py` | Start, stop, restart operations |
| `04_enable_disable.py` | Enable/disable services |
| `09_health_check.py` | Monitor service health |
| `10_failed_units_report.py` | Report failed units |
| `14_batch_operations.py` | Batch manage multiple services |

## Journal

| Script | Description |
|--------|-------------|
| `05_journal_query.py` | Query journal with filters |
| `06_journal_follow.py` | Follow journal in real-time (sync) |
| `11_journal_grep.py` | Search journal with regex |
| `12_journal_reader_lowlevel.py` | Low-level JournalReader usage |

## Async

| Script | Description |
|--------|-------------|
| `07_async_client.py` | Concurrent queries with AsyncSystemdClient |
| `08_async_follow.py` | Follow journal asynchronously |
| `15_async_monitor_dashboard.py` | Async dashboard monitoring |

## Unit File Builder (v0.3.0+)

| Script | Description |
|--------|-------------|
| `16_create_service.py` | Create and deploy a .service unit |
| `17_create_timer.py` | Create a daily backup timer |

## Transient Units & Resources (v0.4.0+)

| Script | Description |
|--------|-------------|
| `18_transient_run.py` | Run commands as transient services |
| `19_resource_monitor.py` | Monitor resource usage |

## Security & Notify (v0.6.0+)

| Script | Description |
|--------|-------------|
| `20_security_audit.py` | Security audit of all services |
| `21_notify_service.py` | Python service with sd_notify |

## Full Workflow

| Script | Description |
|--------|-------------|
| `13_deploy_and_manage.py` | Deploy workflow (enable, start, monitor) |
| `22_full_deploy.py` | Complete lifecycle: create, install, start, monitor |

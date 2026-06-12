# Netty Server CLI — Test Plan

## Test Categories

### 1. Unit Tests (`test_core.py`)

| # | Test | Description | Expected |
|---|------|-------------|----------|
| 1 | `test_session_init` | Session starts with default values | No current SN, empty history |
| 2 | `test_session_set_device` | Setting a device SN updates state | SN stored, known_devices grows |
| 3 | `test_session_undo_redo` | Undo reverts state, redo restores | Roundtrip preserves original |
| 4 | `test_session_clear_history` | Clear empties history | Empty list, no last command |
| 5 | `test_log_entry_creation` | LogEntry dataclass fields | All fields accessible |
| 6 | `test_log_reader_parse` | Parse sample log entries | Correctly extracts event types |
| 7 | `test_log_reader_timestamp` | Timestamps parse correctly | datetime object with correct values |
| 8 | `test_log_reader_summary` | Summary counts events correctly | Event counts match input |
| 9 | `test_http_client_init` | Client initializes with host/port | Base URL correct |
| 10 | `test_command_result` | CommandResult dataclass | All fields accessible |
| 11 | `test_cli_version` | CLI has version flag | No error |
| 12 | `test_log_entry_empty_data` | Log entry with empty receive/send | No crashes |
| 13 | `test_log_reader_no_file` | Non-existent log file returns empty | Empty list |
| 14 | `test_session_json_toggle` | JSON output toggle works | Flag flips correctly |
| 15 | `test_session_server_config` | Setting server host/port | Values stored correctly |

### 2. End-to-End Tests (`test_full_e2e.py`)

| # | Test | Description | Prerequisites |
|---|------|-------------|---------------|
| 1 | `test_cli_installed` | CLI entry point exists | `pip install -e .` done |
| 2 | `test_cli_help` | `--help` shows all commands | Installation |
| 3 | `test_cli_devices_list` | List devices against live server | Running Netty server on :8235 |
| 4 | `test_cli_devices_status` | Status endpoint works | Running server |
| 5 | `test_cli_command_detail` | Send detail command | Running server + online device |
| 6 | `test_cli_command_force` | Send force command | Running server + online device |
| 7 | `test_cli_command_custom` | Send custom JSON | Running server |
| 8 | `test_cli_logs_show` | Show device logs | Log files exist |
| 9 | `test_cli_logs_list_devices` | List log devices | Log files exist |
| 10 | `test_cli_server_info` | Server info output | Running server |
| 11 | `test_cli_json_output` | `--json` flag formats as JSON | Running server |
| 12 | `test_cli_repl_help` | REPL mode accepts `help` | Installation |

## Running Tests

```bash
# Unit tests (no server needed)
cd agent-harness
python -m pytest tests/test_core.py -v

# Full E2E tests (server must be running)
python -m pytest tests/test_full_e2e.py -v

# All tests
python -m pytest tests/ -v
```

## Test Configuration

E2E tests expect:
- Netty server running at `localhost:8235`
- Log files present in `../../../log/` (relative to tests/) or custom `NETTY_LOG_DIR`
- Optional: at least one device online for command tests

Set environment variables to customize:
- `NETTY_HOST` — server hostname (default: `localhost`)
- `NETTY_PORT` — HTTP API port (default: `8235`)
- `NETTY_LOG_DIR` — path to log directory (default: auto-detect)

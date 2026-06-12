---
name: cli-anything-netty-server
description: CLI-Anything harness for the Netty-based IoT device server — manage devices, send commands, check logs
---

# cli-anything-netty-server

Package-local skill definition for the Netty Server CLI harness.

Use this tool to manage IoT devices connected to the Netty TCP server via its HTTP command API (port 8235).

## Commands

| Command | Description |
|---------|-------------|
| `devices list` | List all online device serial numbers |
| `devices status` | Show online/offline status for every known device |
| `command send <sn> <cmd>` | Send a structured command (detail, force, rent, return, heartbeat) |
| `command custom <sn> <json>` | Send raw JSON data to a device |
| `logs show <sn>` | Show device logs (supports --date, --tail, --event filters) |
| `logs list-devices` | List all devices with log files |
| `logs events <sn>` | Show recent event timeline for a device |
| `server info` | Show server connection info and online count |
| `session undo/redo/status` | Undo/redo session state changes |

All commands support `--json` for machine-readable output.

## Examples

```bash
# List devices with JSON output
cli-anything-netty-server devices list --json

# Send a force-release command
cli-anything-netty-server command send CT712507110001 force --n 1

# Show heart events only
cli-anything-netty-server logs show ZCG0422412160066 --event heart --tail 5
```

## Source

- `utils/http_client.py` — HTTP client for the Device Command API
- `utils/log_reader.py` — Log file parser
- `core/session.py` — Session state with undo/redo
- `netty_server_cli.py` — Main Click CLI definition

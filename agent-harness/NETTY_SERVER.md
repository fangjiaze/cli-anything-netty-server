# Netty Server — IoT Device Communication Server

## Overview

This is a Java + Netty-based TCP server that manages IoT device communications.
Devices connect via TCP (port 8234), and an embedded HTTP command server
(port 8235) provides a REST API for external tools (like this CLI harness).

## Architecture

```
TCP Device (8234) ──────▶  NettyTcpServer  ◀────── HTTP Command API (8235)
                                │
                                ▼
                    DeviceConnectionManager
                    (ConcurrentHashMap<sn, Channel>)
                                │
                                ▼
                    Per-device log files (log/YYYY-MM-DD/<sn>.log)
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| **NettyTcpServer** | `NettyTcpServer.java` | Main entry point; starts TCP listener and HTTP command server |
| **NettyTcpServerHandler** | `NettyTcpServerHandler.java` | Processes device messages, handles login/heartbeat/detail/detailup |
| **DeviceConnectionManager** | `DeviceConnectionManager.java` | In-memory device registry; manages channels and message counters |
| **DeviceCommandServer** | `DeviceCommandServer.java` | HTTP API (port 8235) for external commands |
| **IoTMessageDecoder** | `IoTMessageDecoder.java` | Custom message decoder for `#$...$#` and `#*...*#` formats |
| **Config** | `Config.java` | Reads `config.properties` for port, log dir, etc. |

### Message Protocol

Devices communicate using framed messages:
- Format: `#$<JSON>$#` or `#*<JSON>*#`
- JSON payload contains `cmd`, `sn`, `msg` (sequence), `data`, `aims`

### Known Commands (device ↔ server)

| Command | Direction | Purpose |
|---------|-----------|---------|
| `login` | Device → Server | Device authentication & registration |
| `heart` / `heartbeat` | Device → Server | Keep-alive; server responds with `{r:0}` |
| `detail` | Server → Device | Request device detail data |
| `detailup` | Device → Server | Upload detail data (response to detail) |
| `force` | Server → Device | Force-release a port (e.g., `{n: 1}`) |
| `rent` | Server → Device | Lock a port |
| `return` | Server → Device | Unlock a port |

### Device Metadata

On login, devices provide:
- `sn` — serial number (primary key)
- `bn` — batch number (number of AIM groups)
- `num` — items per group (default 4)
- `type` — device model (e.g., "CT59-4PIN")
- `fw` — firmware version
- `mft`, `mod`, `hd`, `ccid`, `imei`, `apn`, etc.

## HTTP API (port 8235)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/debug/connections` | List online device SNs |
| `GET` | `/api/device/status` | Device online/offline status map |
| `POST` | `/api/device/command` | Send structured command (body: `{sn, cmd, data?}`) |
| `POST` | `/api/device/custom-command` | Send raw JSON data (body: `{sn, jsonData}`) |
| `POST` | `/api/device/response` | Internal: Netty stores device responses here |

The command endpoint waits up to 12 seconds for a device response. If the device
is offline, the command is still sent (the server writes it to the TCP buffer)
but returns a warning.

## Log System

Logs are written to `log/<YYYY-MM-DD>/<SN>.log` with entries containing:
- Timestamp
- Client ID and IP
- Event type (login, heart, detailup, detail, disconnect, send, etc.)
- Receive data (JSON from device)
- Send data (JSON to device)

Old logs (older than 15 days) are automatically cleaned up by the server.

## Configuration

File: `config.properties`

```properties
netty.port=8234
command.http.port=8235
log.dir=/var/log/iot-server        (adjusted to "log" in practice)
web.server.url=http://web-server:8082
online.devices.file=online_devices.txt
```

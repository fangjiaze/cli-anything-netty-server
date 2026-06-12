# Netty Server CLI — `cli-anything-netty-server`

**CLI-Anything** 为 Netty IoT 设备通信服务器生成的命令行工具。

通过封装服务器 HTTP 命令 API（端口 **8235**），实现以下功能：

- 🔌 **查看在线设备** — 查看当前连接的 IoT 设备
- 📟 **发送指令** — 支持 `detail`、`force`、`rent`、`return`、心跳、自定义 JSON
- 📋 **查询设备状态** — 实时查看设备的在线/离线状态
- 📜 **读取设备日志** — 按设备查看带时间戳的日志文件
- 🖥️ **交互式 REPL** — 交互式 Shell，方便日常运维
- 📊 **JSON 输出** — 所有命令支持 `--json` 参数，便于脚本调用

## 快速开始

```bash
# 安装 CLI
pip install -e <path-to>/netty-server/agent-harness

# 列出在线设备
cli-anything-netty-server devices list

# 向设备发送 detail 指令
cli-anything-netty-server command send ZCG0422412160066 detail

# 查看设备日志
cli-anything-netty-server logs show ZCG0422412160066

# 指定远程服务器地址
cli-anything-netty-server --host 148.70.196.152 devices list

# 进入交互式 REPL
cli-anything-netty-server
```

## 命令参考

### `devices` — 设备管理

| 子命令 | 说明 |
|--------|------|
| `devices list` | 列出所有当前在线的设备（显示 SN） |
| `devices status` | 显示所有已知设备的在线/离线状态 |
| `devices info <sn>` | 显示指定设备的详细信息 |

### `command` — 指令发送

| 子命令 | 说明 |
|--------|------|
| `command send <sn> <cmd>` | 发送结构化指令。支持的指令：`detail`（请求详情）、`heart`（心跳）、`force`（强制释放端口，需 `--n`）、`rent`（锁定端口，需 `--n`）、`return`（解锁端口，需 `--n`） |
| `command custom <sn> <json-data>` | 发送原始 JSON 数据到设备 |

示例：
```bash
# 请求设备详情
cli-anything-netty-server command send CT902605150001 detail

# 锁定端口 1
cli-anything-netty-server command send CT902605150001 rent --n 1

# 发送自定义 JSON
cli-anything-netty-server command custom CT902605150001 '{"cmd":"heart","data":{"csq":30}}'
```

### `logs` — 日志查看

| 子命令 | 说明 |
|--------|------|
| `logs show <sn>` | 显示设备日志。可选参数：`--date YYYY-MM-DD`（按日期过滤）、`--tail N`（只显示最后 N 条）、`--event TYPE`（按事件类型过滤：login、heart、detailup、detail、disconnect、send） |
| `logs list-devices` | 列出所有有日志文件的设备 |
| `logs dates <sn>` | 显示设备日志的可用日期 |
| `logs search <sn> <keyword>` | 在日志中搜索关键词 |

示例：
```bash
# 查看设备今天的所有日志
cli-anything-netty-server logs show CT902605150001

# 只查看最近 5 条登录日志
cli-anything-netty-server logs show CT902605150001 --tail 5 --event login

# 按日期查看
cli-anything-netty-server logs show CT902605150001 --date 2026-06-11
```

### `server` — 服务器管理

| 子命令 | 说明 |
|--------|------|
| `server ping` | 检测服务器是否可达 |
| `server config` | 显示当前连接配置 |
| `server connect` | 测试与服务器的连接 |

### `session` — 会话管理（REPL 模式）

| 子命令 | 说明 |
|--------|------|
| `session undo` | 撤销上一次操作 |
| `session redo` | 重做上一次撤销 |
| `session clear` | 清空会话历史 |
| `session show` | 显示当前会话状态 |
| `session json` | 以 JSON 格式导出会话 |

## 架构说明

```
┌──────────────────────┐     HTTP (端口 8235)     ┌─────────────────────┐
│  cli-anything-       │ ───────────────────────▶  │  Netty TCP 服务器  │
│  netty-server CLI    │ ◀───────────────────────  │  (Java + Netty)    │
│  (Python / Click)    │                            │                     │
└──────────────────────┘                            │  ┌───────────────┐  │
                                                    │  │ 设备连接管理  │  │
┌──────────────────────┐    读取日志文件              │  │ DeviceConn-   │  │
│  日志读取工具        │ ────────────────────────▶  │  │ ectionMgr    │  │
│  (解析 *.log)        │                            │  └───────────────┘  │
└──────────────────────┘                            │                     │
                                                    │  TCP :8234         │
                                                    │  ───────▶ 设备    │
                                                    └─────────────────────┘
```

- CLI 通过 **HTTP 命令 API**（`DeviceCommandServer.java`，端口 8235）与服务器通信
- 服务器通过 **TCP**（端口 8234）管理设备连接
- 设备日志存储在 `log/` 目录下（按日期分目录）

## 远程连接

默认连接本地服务器 (`localhost:8235`)。如需连接远程服务器：

```bash
# 连接远程服务器
cli-anything-netty-server --host 148.70.196.152 devices list --json

# 指定自定义端口
cli-anything-netty-server --host 148.70.196.152 --port 8235 devices list
```

## 依赖要求

- Python 3.8+
- `click>=8.1`
- 运行中的 Netty TCP 服务器（默认地址：`localhost:8235`）
- 如需连接远程服务器，确保网络可达

## 许可证

MIT

---
name: cli-anything-netty-server
description: IoT Netty Server CLI — 管理设备、发送指令、查看日志（自动安装）
run_as: subagent
allowed_tools: [run_command, read_file, write_file]
---

# cli-anything-netty-server

IoT 设备通信服务器（Netty）的命令行管理工具。

## 首次使用自动安装

当你被调用时，执行以下步骤：

**步骤 1：检查环境**
```bash
python -m cli_anything.netty_server --help
```
- 如果命令可用，跳到步骤 3
- 如果不可用，继续步骤 2

**步骤 2：安装 CLI**
```bash
# 优先尝试从本地源码安装
pip install -e agent-harness/ 2>/dev/null && echo "本地安装成功" || pip install git+https://github.com/<你的GitHub用户名>/cli-anything-netty-server.git 2>/dev/null && echo "Git安装成功" || echo "请先将agent-harness放到当前目录下"
```

如果本地安装失败，尝试从 Git 安装。如果都没有，告知用户手动安装方式。

**步骤 3：执行命令**

`arguments` 参数就是传给 CLI 的命令行参数。将其直接拼接到 `python -m cli_anything.netty_server` 后面执行：

```bash
# 示例：查询在线设备（替换为你的服务器 IP）
python -m cli_anything.netty_server --host <server-ip> devices list --json

# 示例：查看日志
python -m cli_anything.netty_server --host <server-ip> logs show CT902605150001
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `devices list` | 列出在线设备 |
| `devices status` | 显示所有设备状态 |
| `devices info <sn>` | 显示设备详情 |
| `command send <sn> <cmd>` | 发送指令（detail/force/rent/return/heart） |
| `command custom <sn> <json>` | 发送自定义 JSON |
| `logs show <sn>` | 查看日志（--date / --tail / --event） |
| `logs list-devices` | 列出有日志的设备 |
| `server ping` | 检测服务器连通性 |
| `server config` | 查看当前连接配置 |

所有命令支持 `--json` 参数。

## 默认服务器

- 默认地址：`localhost:8235`
- 通过 `--host` 参数指定远程服务器：`python -m cli_anything.netty_server --host <服务器IP> <command>`

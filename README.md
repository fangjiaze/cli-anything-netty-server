# cli-anything-netty-server 一键技能包

Netty IoT 服务器命令行管理工具 — **一条命令安装，所有项目可用**。

## ✨ 特性

- **零配置安装** — 一行命令装好 Python CLI + Reasonix 技能
- **全局可用** — 装一次，所有项目都能调
- **远程连接** — 内置 `--host` 参数，连公网服务器
- **自动补全** — 交互式 REPL + 标准 `--help`

## 🚀 安装

### Windows

```powershell
.\install.ps1
```

### Linux / macOS

```bash
bash install.sh
```

### 或者从 GitHub 安装（如果已发布）

```bash
npx skills add <your-org>/cli-anything-netty-server --skill cli-anything-netty-server -g -y
pip install cli-anything-netty-server
```

## 🎯 使用

### 在 Reasonix 中调用

```bash
# 查在线设备
run_skill({ name: "cli-anything-netty-server", arguments: "--host 148.70.196.152 devices list" })

# 查看设备日志
run_skill({ name: "cli-anything-netty-server", arguments: "--host 148.70.196.152 logs show CT902605150001" })

# 发送指令
run_skill({ name: "cli-anything-netty-server", arguments: "--host 148.70.196.152 command send CT902605150001 detail" })
```

### 在终端中直接使用

```bash
python -m cli_anything.netty_server --host 148.70.196.152 devices list --json
```

### 进入交互模式

```bash
python -m cli_anything.netty_server --host 148.70.196.152
```

## 📋 命令一览

| 命令 | 说明 |
|------|------|
| `devices list` | 列出在线设备 |
| `devices status` | 设备状态 |
| `devices info <sn>` | 设备详情 |
| `command send <sn> <cmd>` | 发送指令 |
| `command custom <sn> <json>` | 自定义指令 |
| `logs show <sn>` | 查看日志 |
| `logs list-devices` | 日志设备列表 |
| `server ping` | 服务器连通性 |

## 📦 发布到 GitHub

想让大家一条命令安装（`npx skills add`）？把本项目推送到 GitHub 即可：

```bash
git init
git add .
git commit -m "Initial commit: cli-anything-netty-server skill"
git remote add origin https://github.com/<你的用户名>/cli-anything-netty-server.git
git push -u origin main
```

然后使用者只需：

```bash
npx skills add <你的用户名>/cli-anything-netty-server --skill cli-anything-netty-server -g -y
pip install git+https://github.com/<你的用户名>/cli-anything-netty-server.git
```

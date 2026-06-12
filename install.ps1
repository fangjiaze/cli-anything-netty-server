# cli-anything-netty-server 一键安装脚本 (Windows)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Join-Path $env:USERPROFILE ".reasonix\skills\cli-anything-netty-server"
$harnessDir = Join-Path $scriptDir "agent-harness"

Write-Host "=== 安装 cli-anything-netty-server ===" -ForegroundColor Cyan

# 1. 安装 Python CLI 包
Write-Host "[1/3] 安装 Python CLI 包..." -ForegroundColor Yellow
if (Test-Path $harnessDir) {
    pip install -e $harnessDir
} else {
    Write-Host "  agent-harness 目录不存在，尝试从 pip 安装..." -ForegroundColor Yellow
    pip install cli-anything-netty-server 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠  pip 安装失败，请先将 agent-harness 放到本目录同级" -ForegroundColor Red
    }
}

# 2. 安装 Reasonix 技能
Write-Host "[2/3] 安装 Reasonix 技能..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
Copy-Item (Join-Path $scriptDir "SKILL.md") (Join-Path $skillDir "SKILL.md") -Force

# 3. 验证
Write-Host "[3/3] 验证安装..." -ForegroundColor Yellow
python -m cli_anything.netty_server --help 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ CLI 可用" -ForegroundColor Green
} else {
    Write-Host "  ⚠  CLI 验证失败，请检查 Python 环境" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Green
Write-Host "重启 Reasonix 后即可使用以下命令调用：" -ForegroundColor Cyan
Write-Host '  run_skill({ name: "cli-anything-netty-server", arguments: "--host 148.70.196.152 devices list" })'

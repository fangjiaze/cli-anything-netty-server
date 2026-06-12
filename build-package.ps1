# 构建完整的一键安装包 — 将 agent-harness 打包到技能目录
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceHarness = "D:\VScode_Project\Trae\GT04\netty-server\agent-harness"
$destHarness = Join-Path $scriptDir "agent-harness"

Write-Host "=== 构建 cli-anything-netty-server 安装包 ===" -ForegroundColor Cyan

# 复制 agent-harness
Write-Host "[1/3] 打包 Python CLI 源码..." -ForegroundColor Yellow
if (Test-Path $destHarness) {
    Remove-Item -Path $destHarness -Recurse -Force
}
Copy-Item -Path $sourceHarness -Destination $destHarness -Recurse

# 清理不必要的文件
$exclude = @("__pycache__", "*.pyc", ".pytest_cache", "*.egg-info")
Get-ChildItem -Path $destHarness -Recurse -Directory | 
    Where-Object { $_.Name -in $exclude -or $_.Name -like "*.egg-info" } | 
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[2/3] 打包技能文件..." -ForegroundColor Yellow
# SKILL.md 和 install.ps1 已经在目录中了

Write-Host "[3/3] 验证包结构..." -ForegroundColor Yellow
$tree = Get-ChildItem -Path $scriptDir -Recurse -File | ForEach-Object { $_.FullName.Replace($scriptDir, "") }
$tree | ForEach-Object { Write-Host "  $_" }

Write-Host ""
Write-Host "=== 构建完成 ===" -ForegroundColor Green
Write-Host "目录: $scriptDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "发布到 GitHub 后，用户即可一行命令安装：" -ForegroundColor Yellow
Write-Host '  npx skills add <你的用户名>/cli-anything-netty-server --skill cli-anything-netty-server -g -y' -ForegroundColor White
Write-Host '  pip install git+https://github.com/<你的用户名>/cli-anything-netty-server.git' -ForegroundColor White

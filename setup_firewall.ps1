# AI-Exam Firewall Setup Script
# 必须以管理员身份运行！
# 作用：确保 AI 考试系统的 3000, 8000, 8001 端口在局域网中完全开放

Write-Host "=== AI-Exam System 防火墙配置脚本 ===" -ForegroundColor Cyan
Write-Host "此脚本将配置 Frontend (3000), Backend (8000), AI-Service (8001) 的入站规则。"
Write-Host ""

# 1. 检查管理员权限
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[错误] 权限不足！请右键点击此脚本，选择“以管理员身份运行”。" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit
}
Write-Host "[1/3] 已获取管理员权限" -ForegroundColor Green

# 2. 清理旧规则（如果存在同名的旧规则，先删除）
Write-Host "[2/3] 清理旧规则..."
Remove-NetFirewallRule -DisplayName "AI-Exam Frontend (3000)" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "AI-Exam Backend (8000)" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "AI-Exam AI-Service (8001)" -ErrorAction SilentlyContinue
Write-Host "      旧规则已清理"

# 3. 添加新规则
Write-Host "[3/3] 添加新规则..."

# Frontend
New-NetFirewallRule -DisplayName "AI-Exam Frontend (3000)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3000 `
    -Action Allow `
    -Profile Any `
    -Description "AI考试系统前端服务" | Out-Null
Write-Host "      [OK] 端口 3000 (Frontend)" -ForegroundColor Green

# Backend
New-NetFirewallRule -DisplayName "AI-Exam Backend (8000)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -Action Allow `
    -Profile Any `
    -Description "AI考试系统后端服务" | Out-Null
Write-Host "      [OK] 端口 8000 (Backend)" -ForegroundColor Green

# AI Service
New-NetFirewallRule -DisplayName "AI-Exam AI-Service (8001)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8001 `
    -Action Allow `
    -Profile Any `
    -Description "AI考试系统AI评分服务" | Out-Null
Write-Host "      [OK] 端口 8001 (AI-Service)" -ForegroundColor Green

Write-Host ""
Write-Host "========================================"
Write-Host "防火墙配置完成！请尝试从其他设备访问：" -ForegroundColor Yellow
Write-Host "http://192.168.1.30:3000"
Write-Host "========================================"
Write-Host ""
Read-Host "按 Enter 键退出"

# =============================================================================
# CivilPDF-DX Windows 11 サービス登録スクリプト (NSSM 使用)
# 実行: PowerShell を「管理者として実行」してから実行
#       .\install-services.ps1
#
# 前提条件:
#   - Python 3.12 インストール済み
#   - Node.js 24.x インストール済み
#   - NSSM (Non-Sucking Service Manager) インストール済み
#     https://nssm.cc/download
#   - .venv 仮想環境セットアップ済み
#     cd <INSTALL_DIR>\src\console\backend
#     python -m venv .venv
#     .venv\Scripts\pip install -r requirements.txt
# =============================================================================

param(
    [string]$InstallDir = "C:\CivilPDF",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5181",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$BackendServiceName  = "CivilPDF-Backend"
$FrontendServiceName = "CivilPDF-Frontend"

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Error "このスクリプトは管理者権限で実行してください。"
    exit 1
}

$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Error "NSSM が見つかりません。https://nssm.cc/download からダウンロードして PATH に追加してください。"
    exit 1
}

# --- アンインストール ---
if ($Uninstall) {
    Write-Host "サービスを停止・削除します..." -ForegroundColor Yellow
    foreach ($svc in @($BackendServiceName, $FrontendServiceName)) {
        $existing = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($existing) {
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
            & nssm remove $svc confirm
            Write-Host "  削除: $svc" -ForegroundColor Green
        }
    }
    Write-Host "アンインストール完了。" -ForegroundColor Green
    exit 0
}

# --- パス設定 ---
$BackendDir  = Join-Path $InstallDir "src\console\backend"
$FrontendDir = Join-Path $InstallDir "src\console\frontend"
$VenvPython  = Join-Path $InstallDir ".venv\Scripts\python.exe"
$NodePath    = (Get-Command node -ErrorAction Stop).Source
$NpmPath     = Join-Path (Split-Path $NodePath) "npm.cmd"
$LogDir      = Join-Path $InstallDir "logs"

# ログディレクトリ作成
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# --- バックエンドサービス登録 ---
Write-Host "`n[1/2] バックエンドサービスを登録中..." -ForegroundColor Cyan

$existing = Get-Service -Name $BackendServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Service -Name $BackendServiceName -Force -ErrorAction SilentlyContinue
    & nssm remove $BackendServiceName confirm
}

& nssm install $BackendServiceName $VenvPython
& nssm set $BackendServiceName AppParameters "-m uvicorn main:app --host 0.0.0.0 --port $BackendPort --workers 2"
& nssm set $BackendServiceName AppDirectory $BackendDir
& nssm set $BackendServiceName AppEnvironmentExtra "PYTHONPATH=$BackendDir"
& nssm set $BackendServiceName AppStdout (Join-Path $LogDir "backend-stdout.log")
& nssm set $BackendServiceName AppStderr (Join-Path $LogDir "backend-stderr.log")
& nssm set $BackendServiceName AppRotateFiles 1
& nssm set $BackendServiceName AppRotateBytes 10485760
& nssm set $BackendServiceName Start SERVICE_AUTO_START
& nssm set $BackendServiceName Description "CivilPDF-DX FastAPI Backend (port $BackendPort)"

Write-Host "  ✅ $BackendServiceName 登録完了" -ForegroundColor Green

# --- フロントエンドサービス登録 ---
Write-Host "`n[2/2] フロントエンドサービスを登録中..." -ForegroundColor Cyan

$existing = Get-Service -Name $FrontendServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Service -Name $FrontendServiceName -Force -ErrorAction SilentlyContinue
    & nssm remove $FrontendServiceName confirm
}

& nssm install $FrontendServiceName $NpmPath
& nssm set $FrontendServiceName AppParameters "run dev:lan"
& nssm set $FrontendServiceName AppDirectory $FrontendDir
& nssm set $FrontendServiceName AppStdout (Join-Path $LogDir "frontend-stdout.log")
& nssm set $FrontendServiceName AppStderr (Join-Path $LogDir "frontend-stderr.log")
& nssm set $FrontendServiceName AppRotateFiles 1
& nssm set $FrontendServiceName AppRotateBytes 10485760
& nssm set $FrontendServiceName Start SERVICE_AUTO_START
& nssm set $FrontendServiceName Description "CivilPDF-DX Vite Frontend (port $FrontendPort)"
& nssm set $FrontendServiceName AppDependencies $BackendServiceName

Write-Host "  ✅ $FrontendServiceName 登録完了" -ForegroundColor Green

# --- Firewall ルール追加 ---
Write-Host "`nWindows Firewall ルールを設定中..." -ForegroundColor Cyan

foreach ($rule in @(
    @{ Name="CivilPDF Backend";  Port=$BackendPort  },
    @{ Name="CivilPDF Frontend"; Port=$FrontendPort }
)) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if ($existing) { Remove-NetFirewallRule -DisplayName $rule.Name }
    New-NetFirewallRule `
        -DisplayName $rule.Name `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $rule.Port `
        -Action Allow `
        -Profile Domain,Private | Out-Null
    Write-Host "  ✅ Firewall: $($rule.Name) port $($rule.Port)" -ForegroundColor Green
}

# --- サービス起動 ---
Write-Host "`nサービスを起動中..." -ForegroundColor Cyan
Start-Service -Name $BackendServiceName
Start-Sleep -Seconds 3
Start-Service -Name $FrontendServiceName

$b = Get-Service -Name $BackendServiceName
$f = Get-Service -Name $FrontendServiceName
Write-Host "`n=== サービス状態 ===" -ForegroundColor White
Write-Host "  $BackendServiceName  : $($b.Status)"
Write-Host "  $FrontendServiceName : $($f.Status)"

Write-Host "`n✅ インストール完了!" -ForegroundColor Green
Write-Host "  バックエンド: http://localhost:$BackendPort"
Write-Host "  フロントエンド: http://localhost:$FrontendPort"
Write-Host "  ログ: $LogDir"

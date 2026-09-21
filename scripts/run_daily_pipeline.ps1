# Chạy daily pipeline một lần (Windows). Dùng với Task Scheduler sau 15:00 GMT+7.
# Ví dụ đăng ký (chỉnh đường dẫn repo):
#   schtasks /Create /TN "VNSignalDaily" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:15 ^
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Projects\Telegram-bot-for-investment-signal\scripts\run_daily_pipeline.ps1" /F

param(
    [switch]$WithSector,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $Python = $venvPython
} else {
    $Python = "python"
}

$argsList = @("scripts\run_daily_pipeline.py")
if ($WithSector) { $argsList += "--with-sector" }
if ($NoPush) { $argsList += "--no-push" }

Write-Host "cwd=$Root"
Write-Host "python=$Python $($argsList -join ' ')"
& $Python @argsList
exit $LASTEXITCODE

param(
    [string]$StartDate = "2026-01-02",
    [string]$EndDate = "2026-04-30"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd"
$LogPath = Join-Path $LogDir "daily_routine_$Stamp.log"

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . ".\.venv\Scripts\Activate.ps1"
}

python -m src.scanners.daily_quant_routine `
    --start $StartDate `
    --end $EndDate `
    --with-regimes `
    --with-event-context `
    --with-governance `
    --save-db `
    --csv *>> $LogPath

exit $LASTEXITCODE

$ErrorActionPreference = "Stop"

$env:SHOESME_BOT_HEADLESS = "0"
$env:SHOESME_BOT_BATCH = "1"
$env:SHOESME_BOT_WAIT = "5"
$env:SHOESME_BOT_CACHE = "1"

Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$cdp = "http://127.0.0.1:9222/json/version"
$needs_browser = $true
try {
    Invoke-RestMethod -Uri $cdp -TimeoutSec 2 | Out-Null
    $needs_browser = $false
} catch {
    $needs_browser = $true
}

if ($needs_browser) {
    Write-Host "Opening Shoesme debug browser..."
    & (Join-Path $PSScriptRoot "open_shoesme_chrome_debug.ps1")
    Start-Sleep -Seconds 3
}

Write-Host "Starting Shoesme crawler..."
python -u (Join-Path $PSScriptRoot "..\3_shoesme_botasaurus.py")

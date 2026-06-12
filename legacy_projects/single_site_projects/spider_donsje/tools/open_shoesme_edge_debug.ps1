$edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) {
    $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
}
if (-not (Test-Path $edge)) {
    $edge = "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
}
if (-not (Test-Path $edge)) {
    throw "Edge not found"
}

$profile = Join-Path $PSScriptRoot "shoesme_cdp_edge_profile"
New-Item -ItemType Directory -Force -Path $profile | Out-Null

Start-Process -FilePath $edge -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=$profile",
    "--no-first-run",
    "--no-default-browser-check",
    "--window-position=-32000,-32000",
    "--window-size=1200,900",
    "https://www.shoesme.nl/"
) -WindowStyle Minimized

Write-Host "Edge opened minimized. Restore it once to finish verification if needed, then minimize it again and run:"
Write-Host '$env:SHOESME_CDP_ENDPOINT="http://127.0.0.1:9222"; python .\3_xenos.py'

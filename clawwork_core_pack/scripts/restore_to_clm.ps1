param(
  [Parameter(Mandatory=$true)]
  [string]$TargetRoot,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$packRoot = Split-Path -Parent $PSScriptRoot
$payload = Join-Path $packRoot "payload"
$target = (Resolve-Path $TargetRoot).Path

if (-not (Test-Path $payload)) {
  throw "Payload directory not found: $payload"
}

Get-ChildItem $payload -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($payload.Length).TrimStart("\")
  $dest = Join-Path $target $rel
  if ($DryRun) {
    Write-Host "COPY $rel"
  } else {
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
  }
}

if ($DryRun) {
  Write-Host "Dry run complete. No files copied."
} else {
  Write-Host "Restore complete: $target"
}

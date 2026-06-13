# CLM Stress Assets Backup - 2026-06-13

This private package contains the former public `dev_logs/stress/` assets from
Crawler-Mind / CLM.

## Origin

- Source project: Crawler-Mind / CLM
- Source remote: https://github.com/32872-del/CrawlerMind.git
- Source path: `F:\datawork\agent\dev_logs\stress`
- Created at: 2026-06-13

## Contents

- `2026-05-09_local_stress_test_report.md`
- `2026-05-09_local_stress_test_summary.json`
- `2026-05-09_stress_export_30000.xlsx`

These are run artifacts from CLM stress testing. They are useful for private
regression review and performance-history comparison, but they are not needed
for a clean public source checkout.

## Restore Into A CLM Checkout

From this private repository root:

```powershell
$clm = "F:\datawork\agent"
New-Item -ItemType Directory -Force -Path "$clm\dev_logs" | Out-Null
Copy-Item -LiteralPath ".\stress_assets_20260613\dev_logs_stress" `
  -Destination "$clm\dev_logs\stress" `
  -Recurse -Force
```

## Integrity

Use `MANIFEST.json` and `SHA256SUMS.json` to verify file count, byte size, and
SHA256 before using the assets as evidence.

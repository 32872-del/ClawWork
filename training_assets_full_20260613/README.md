# CLM Full Training Assets Backup - 2026-06-13

This private package contains the full `dev_logs/training/` directory copied
from Crawler-Mind before removing those assets from the public repository.

## Origin

- Source project: Crawler-Mind / CLM
- Source remote: https://github.com/32872-del/CrawlerMind.git
- Source path: `F:\datawork\agent\dev_logs\training`
- Source commit at first packaging: `fd1d6816082be5055908f82ac091a31af76f4646`
- Created at: 2026-06-13T16:15:35+08:00
- Verified against public workspace on: 2026-06-13

## Verification Result

The package was compared against `F:\datawork\agent\dev_logs\training` by
relative path, byte size, and SHA256.

- Public file count: 960
- Private file count: 960
- Missing in private: 0
- Extra in private: 0
- Hash mismatches: 0
- Total bytes: 581,051,102

`SHA256SUMS.json` and `MANIFEST.json` are the authoritative integrity records.

## Contents

This package preserves CLM's private training and evidence lake:

- real-site training runs
- ecommerce extraction results
- large visual recon screenshot sets
- Xiaomi-model generated visual reconnaissance data
- managed-loop E2E results
- extraction contract datasets
- profile/replay/API/XHR evidence
- failure taxonomies and batch summaries
- generated `.xlsx` exports used for capability checks

The public repository should keep only sanitized examples and documentation.
These files are training evidence, real-site recon records, visual evidence,
contract samples, and generated exports that belong in the owner's private
asset store.

## Restore Into A CLM Checkout

From this private repository root:

```powershell
$clm = "F:\datawork\agent"
New-Item -ItemType Directory -Force -Path "$clm\dev_logs" | Out-Null
Copy-Item -LiteralPath ".\training_assets_full_20260613\dev_logs_training" `
  -Destination "$clm\dev_logs\training" `
  -Recurse -Force
```

If `dev_logs\training` already exists in the target checkout, back it up first
or remove it before restoring this package.

## Use Without Restoring

For future training, audits, and fixture generation, prefer reading this package
directly as a private data lake:

```text
ClawWork/training_assets_full_20260613/dev_logs_training
```

Do not copy generated screenshots, large exports, or real-site evidence back
into the public CrawlerMind repository unless they have been explicitly
sanitized and intentionally approved for public release.

## Relationship To Public CrawlerMind

CrawlerMind should remain runnable as a public Community edition. This package
preserves private evidence and training material so future private/enterprise
development can continue without exposing the owner's collected datasets.

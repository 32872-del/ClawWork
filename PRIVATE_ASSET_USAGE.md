# CLM Private Asset Usage Guide

This repository is the private asset store for CLM / CrawlerMind. It keeps
advanced implementation packages, legacy crawler know-how, training data,
screenshots, stress outputs, and restoration context that should not live in the
public Community repository.

## Current Private Packages

### `clawwork_core_pack/`

Private preservation package for advanced CLM crawler backend and project
context.

Use it when a CLM checkout needs private implementation files restored or when
building a future `clm_private_core` package.

Restore command:

```powershell
powershell -ExecutionPolicy Bypass -File .\clawwork_core_pack\scripts\restore_to_clm.ps1 -TargetRoot F:\datawork\agent
```

### `training_assets_full_20260613/`

Full private backup of `F:\datawork\agent\dev_logs\training`.

Use it as the private training/evidence lake for:

- fixture generation
- real-site capability regression
- visual recon review
- managed-loop training analysis
- extraction contract research

Restore command:

```powershell
$clm = "F:\datawork\agent"
Copy-Item -LiteralPath ".\training_assets_full_20260613\dev_logs_training" `
  -Destination "$clm\dev_logs\training" `
  -Recurse -Force
```

### `stress_assets_20260613/`

Private backup of former public `F:\datawork\agent\dev_logs\stress`.

Use it for performance-history and long-run regression comparison.

Restore command:

```powershell
$clm = "F:\datawork\agent"
Copy-Item -LiteralPath ".\stress_assets_20260613\dev_logs_stress" `
  -Destination "$clm\dev_logs\stress" `
  -Recurse -Force
```

## Normal Development Rule

For public CrawlerMind development:

1. Keep the public repository runnable without these private packages.
2. Keep demos and tests sanitized.
3. Keep private evidence, screenshots, `.xlsx` outputs, raw site samples, and
   high-value training records in this repository.
4. Before pushing public CrawlerMind, run `git status` and check that
   `dev_logs/training/**` and `dev_logs/stress/**` are not staged.

For private capability development:

1. Restore only the package you need.
2. Use restored files locally as evidence or fixtures.
3. If a derived fixture is suitable for public release, sanitize it first and
   place it under an intentional public examples/tests path.
4. Do not copy this repository into `F:\datawork\agent` as a submodule or
   nested checkout unless the owner explicitly decides to change the repo model.

## Integrity Checks

Each package has a `MANIFEST.json` and `SHA256SUMS.json`.

To verify a restored file manually:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "path\to\file"
```

Compare the result with the matching entry in `SHA256SUMS.json`.

## Ownership

These packages are derived from the CLM workspace and are maintained as
owner-controlled private assets. The public CrawlerMind repository may reference
their existence at a high level, but it should not contain the private payloads.

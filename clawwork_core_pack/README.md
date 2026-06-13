# ClawWork Core Pack

This private package preserves the advanced CLM crawler core assets that should not be treated as the public Community edition.

## Origin

- Source project: Crawler-Mind / CLM
- Source remote: https://github.com/32872-del/CrawlerMind.git
- Source branch: main
- Source commit: a791890cf56b00898562e45d6103e334f1e65a0b
- Source path at packaging time: F:\datawork\agent
- Packaged at: 2026-06-13T15:37:59+08:00

## What This Package Is

This is a private, pluggable core asset package for CLM. It contains selected advanced backend modules, managed workflow assets, training records, reports, and restoration instructions.

The public CrawlerMind repository can remain runnable as CLM Community. This private package keeps higher-value implementation details, training evidence, and future enterprise extensions under the owner's control.

## Included Asset Classes

- CLM-native runtime backend
- managed workflow/runners
- storage/checkpoint/frontier/product store foundations
- LLM/provider/trace interfaces
- API and model schemas needed to understand private extension points
- advanced tool modules: replay, browser evidence, JS evidence, access/proxy/session diagnostics, coverage, quality, extraction contracts
- structured training records and reports, excluding large binary screenshots/exports
- project status, plans, and recovery context

## Excluded By Design

Large generated or runtime artifacts are intentionally excluded:

- screenshots and images
- Excel exports
- SQLite/runtime databases
- Python caches
- temporary logs and archives

If a full forensic backup is needed, create a separate encrypted archive from the original CLM workspace.

## How To Reuse

There are two supported modes.

### Mode A: Restore Into A CLM Checkout

From this repository root:

`powershell
powershell -ExecutionPolicy Bypass -File .\clawwork_core_pack\scripts\restore_to_clm.ps1 -TargetRoot F:\datawork\agent
`

The script copies files from payload/ back to their original paths.

### Mode B: Use As A Private Extension Source

Use payload/ as the source of a private package named clm_private_core or equivalent. Keep public CLM imports stable, then load private strategies through a registry/loader layer.

Recommended future shape:

`	ext
clm_private_core/
  managed_policy/
  repair_policy/
  profile_library/
  replay_advanced/
  browser_profile_advanced/
  training_assets/
`

## Future Split Plan

When splitting this package cleanly from public CLM:

1. Keep public CLM Community runnable with mock/demo/basic runtime.
2. Add a capability registry in public CLM.
3. Move advanced policies and private profiles into clm_private_core.
4. Load private capabilities only when the private package is installed.
5. Keep training datasets and real-site playbooks private.
6. Keep public README honest: Community is runnable; Private Core contains higher-value production assets.

## Ownership Note

This private package is derived from the CLM workspace at the source commit listed above. It is intended as an owner-controlled preservation and development package for advanced CLM capabilities and training assets.

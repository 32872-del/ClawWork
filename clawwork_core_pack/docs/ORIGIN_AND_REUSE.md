# Core Asset Ownership And Restoration Note

This package was created to preserve private CLM core assets separately from the public Community repository.

## Belongs To

- Original project: Crawler-Mind (CLM)
- Original repository: https://github.com/32872-del/CrawlerMind.git
- Original commit: a791890cf56b00898562e45d6103e334f1e65a0b

## Why It Exists

CLM Community should remain runnable and useful for public review. However, advanced crawler capability, real-site training evidence, managed repair strategy, private profiles, and enterprise hardening knowledge should stay under the owner's direct control.

## How To Split Back Into Original Locations

The payload/ directory mirrors original CLM paths. To restore manually, copy any path under payload/ to the same path in a CLM checkout.

Example:

`	ext
payload/autonomous_crawler/runtime -> <CLM>/autonomous_crawler/runtime
payload/docs/plans -> <CLM>/docs/plans
`

Prefer restoring selected directories rather than overwriting an active working tree blindly.

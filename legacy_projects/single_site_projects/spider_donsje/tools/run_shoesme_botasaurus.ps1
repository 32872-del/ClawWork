$env:SHOESME_BOT_HEADLESS = "0"
$env:SHOESME_BOT_BATCH = "1"
$env:SHOESME_BOT_WAIT = "5"

Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

# Optional debug limits. Uncomment for sampling.
# $env:SHOESME_CATEGORY_LIMIT = "1"
# $env:SHOESME_PAGE_LIMIT = "1"
# $env:SPIDER_TEST_LIMIT = "50"

python -u (Join-Path $PSScriptRoot "..\3_shoesme_botasaurus.py")

# ClawWork Crawler Framework

ClawWork is a private reusable product-site crawler framework built around a three-stage collection pipeline:

1. list/category collection
2. product detail collection
3. variant/SKU enrichment and final goods writing

The repository contains the shared framework under `fnspider/`, site adapters named like `29_obi.py` and `67_lomar.py`, repair/export utilities under `tools/`, and project documentation.

## What This Framework Does

The framework is designed for e-commerce product collection. A site script focuses on site-specific parsing, while `fnspider` provides common runtime capabilities:

- task queues for category, product, and variant stages
- resumable progress stored in SQLite
- duplicate detection by stable `sole_id`
- request abstraction for `requests`, `curl_cffi`, Botasaurus, Playwright, and Scrapling-style fetchers
- optional local Clash proxy pool and BrightData-style rotating proxy support
- local HTML/cache directories for debugging and repeated runs
- export/repair tools for database cleanup, image download, and import spreadsheets

## Repository Layout

```text
fnspider/          shared crawler framework
tools/             database, image, export, and browser probing utilities
study/             learning notes and crawler engineering study material
NN_site.py         site-specific crawler adapters
*_repair_*.py      one-off or reusable repair scripts for collected data
requirements.txt   Python dependency list
.env.example       local environment variable template
```

Daily runtime outputs are intentionally excluded from Git: `goods/`, `goods_cache/`, `downloadimg/`, `out/`, `upload/`, `logs/`, `browser_profiles/`, databases, spreadsheets, and zip packages. The private proxy pool under `fnspider/clash/` is part of this runnable project and is committed with the code.

## Install

```powershell
cd F:\datawork\spider
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
```

If a script uses browser automation through Botasaurus or Playwright, keep Chrome/Edge available on the machine.

## Configure Local Runtime

The repository is private, so the project keeps the crawler scripts and proxy runtime together. For values that often change between machines or sessions, use `.env` or PowerShell environment variables.

```powershell
$env:HEADLESS = "1"
$env:BATCH = "2"
$env:OBI_COOKIE = "paste_browser_cookie_here"
$env:BRIGHT_USE_PROXY = "1"
$env:BRIGHT_PROXY_URL = "http://username:password@brd.superproxy.io:33335"
```

Do not commit `.env`, browser storage state, generated databases, exported spreadsheets, logs, caches, or downloaded images.

## Run A Site Script

Every main site adapter defines a `CrawlerObject(Spider)` class and usually supports a direct run:

```powershell
python .\67_lomar.py
```

For a small test run, prefer environment limits when the script supports them:

```powershell
$env:BATCH = "1"
$env:WAIT = "1"
$env:OBI_MAX_CATEGORIES = "1"
$env:OBI_MAX_PAGES = "1"
$env:OBI_MAX_PRODUCTS = "20"
python .\29_obi.py
```

Generated SQLite databases are written under the configured output directory and are ignored by Git.

## Add A New Site Adapter

Use an existing recent script as the template, then keep the adapter thin:

- define `PAYLOAD_LIST` or build start URLs from menus/API responses
- subclass `fnspider.Spider`
- implement `get_list`, `get_content`, and `get_more_content`
- normalize fields to the framework schema: `handle`, `title`, `image_src`, `price`, category fields, option fields, and `body`
- add env-driven switches for cookies, auth, browser fallback, proxy use, and small test limits
- keep real auth data out of source code

See `docs/FRAMEWORK_GUIDE.md` for the detailed adapter flow.

## Current Site Assets

The repository includes dozens of site adapters covering static HTML, JSON API, Next.js data extraction, dynamic-browser collection, proxy fallback, cookie-auth flow, and post-collection repair tasks. The detailed project analysis is in `项目采集框架研究报告.md`.

## Private Repository Boundary

This repository is intended as a private work archive and reusable crawler framework. It should include:

- framework source in `fnspider/`
- all site adapter scripts and repair scripts
- proxy pool/runtime files required by your local crawler setup
- documentation, dependency files, and environment templates

It should not include high-volume generated data such as image downloads, SQLite results, cache snapshots, logs, browser profiles, or zip backups.

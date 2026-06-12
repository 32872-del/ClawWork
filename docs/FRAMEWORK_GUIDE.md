# Framework Guide

This document explains how to reuse the existing crawler framework for a new e-commerce site.

## Core Runtime Model

The framework centers on `fnspider.Spider`. A site adapter subclasses it and implements three methods:

- `get_list(params)`: receives a category/list URL and yields product items.
- `get_content(params)`: receives a product/list item and yields one or more normalized product records or variant tasks.
- `get_more_content(params)`: receives variant/SKU tasks and writes final goods rows.

`Spider` manages queues, worker threads, progress marking, duplicate detection, and shutdown. `DataProcessor` creates the output database and writes progress records. `OperateDB` owns the SQLite schema. `NetworkRequest` provides the shared request/browser/proxy entry points.

## Standard Adapter Shape

Each site script normally follows this structure:

```python
from fnspider import Spider

PAYLOAD_LIST = {
    "Category 1": {
        "Subcategory": "https://example.com/category"
    }
}


class CrawlerObject(Spider):
    is_proxy = 0
    collect_thread_number = 2
    more_collect_thread_number = 2
    is_recollect = 1
    name = "_site_name"

    def __init__(self):
        self.start_urls = build_start_urls(PAYLOAD_LIST)
        super().__init__()

    def get_list(self, params):
        yield from parse_list_page(params)

    def get_content(self, params):
        yield from parse_product_page(params)

    def get_more_content(self, params):
        yield normalize_final_goods(params)


if __name__ == "__main__":
    CrawlerObject().main()
```

## Field Contract

Final goods rows should keep these fields stable:

- `url`: product URL
- `handle`: stable product handle
- `title`: product title
- `subtitle`: optional subtitle
- `price`: numeric price where possible
- `body`: cleaned HTML description
- `categories_1`, `categories_2`, `categories_3`: category path
- `option1_name`, `option1_value`, `option2_name`, `option2_value`, `option3_name`, `option3_value`: variant dimensions
- `image_src`: image URLs, usually joined by commas or JSON depending on script convention
- `size_price`: SKU-level stock/price/size JSON when needed
- `more_info`: raw auxiliary payload for debugging or repair

## New Site Workflow

1. Probe the site manually.
   - Identify whether data is in static HTML, JSON API, Next.js payload, GraphQL, or browser-rendered state.
   - Save a few representative pages under `out/` during research.

2. Build category input.
   - Prefer stable menu/API category URLs.
   - Keep `PAYLOAD_LIST` explicit when a site has messy navigation.
   - Generate `start_urls` with category metadata already attached.

3. Implement list parsing.
   - Extract product URL, list title, image, category path, and any product ID.
   - Handle pagination or infinite-scroll API cursors.
   - Add small-run environment limits for testing.

4. Implement detail parsing.
   - Extract title, price, description, images, variant groups, SKU IDs, and stock status.
   - Normalize relative URLs.
   - Clean HTML body and remove scripts, ads, duplicate headings, and unrelated blocks.

5. Implement variant enrichment.
   - Expand colors/sizes/materials as separate final rows when the target import format needs it.
   - Preserve enough `more_info` or `size_price` to repair later without recollecting the whole site.

6. Add anti-bot handling only where needed.
   - Start with normal requests/fetchers.
   - Add headers, cookies, browser fallback, proxy pool, or auth refresh based on actual failure mode.
   - Keep knobs controlled by environment variables so a script can run in test, full, and repair modes.

7. Validate output.
   - Check row count by category.
   - Spot-check product detail pages.
   - Run export/repair tools only after the database content is stable.

## Reuse Patterns Already Present

- Static HTML parsing: early scripts such as `26_kross.py`, `31_eveline.py`.
- JSON/embedded payload parsing: `35_reserved.py`, `39_primark.py`, `50_kruidvat.py`.
- Browser/auth fallback: `48_babyshop.py`, `49_homecentre.py`, `60_chaussea.py`, `63_luvishoes.py`, `64_takistir.py`.
- Proxy rotation and reset handling: `37_aniakruk.py`, `43_banpresto.py`, `46_11teamsports.py`, `60_chaussea.py`.
- Post-collection repair: `46_11teamsports_repair_*.py`, `63_luvishoes_repair_title_body.py`, and tools under `tools/`.

## Engineering Direction

The next step is to gradually move duplicated helper code from individual site scripts into reusable modules:

- cookie parsing and browser auth refresh
- category tree flattening
- product body cleaning
- image normalization and local image repair
- pagination helpers
- variant/SKU normalization
- proxy retry policy
- small-run test switches

Do this incrementally. The current scripts are valuable because they encode many site-specific battle-tested decisions; the framework should absorb repeated patterns without flattening away those details.

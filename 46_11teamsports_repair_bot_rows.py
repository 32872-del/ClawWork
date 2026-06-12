# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sqlite3
import time
from pathlib import Path

from bs4 import BeautifulSoup
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("TEAMS_USE_PROXY", "0")
os.environ.setdefault("TEAMS_RECOLLECT", "0")
os.environ.setdefault("TEAMS_MIN_INTERVAL", "3")
os.environ.setdefault("TEAMS_INTERVAL_JITTER", "2")
os.environ.setdefault("TEAMS_REQUEST_RETRIES", "2")
os.environ.setdefault("TEAMS_BOT_SLEEP", "600")

SCRIPT_PATH = BASE_DIR / "46_11teamsports.py"
DEFAULT_DB = BASE_DIR / "goods" / "1780035610_46_11teamsports.db"


def load_spider_module():
    spec = importlib.util.spec_from_file_location("teams46", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def latest_db():
    files = sorted((BASE_DIR / "goods").glob("*_46_11teamsports.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else DEFAULT_DB


def is_bot_row(row):
    title = (row["title"] or "").lower()
    body = (row["body"] or "").lower()
    return "not a bot" in title or "not a bot" in body


def build_item(mod, row):
    html_text, final_url = mod.fetch_text(row["url"], headers=mod.HTML_HEADERS, referer=mod.HOME_URL, cache=False, kind="repair-detail")
    if mod.is_bad_html(html_text, None):
        raise RuntimeError("still got bot/challenge page")

    soup = BeautifulSoup(html_text, "html.parser")
    ld = mod.product_ld(soup)
    title = mod.extract_title(soup, ld=ld)
    if not title or "not a bot" in title.lower():
        raise RuntimeError(f"bad title: {title!r}")

    price = mod.extract_price(soup, row["price"], ld=ld)
    if price is None:
        raise RuntimeError("price is empty")

    images = mod.extract_images(soup, ld=ld)
    if not images:
        raise RuntimeError("images are empty")

    color = mod.extract_color(soup)
    sizes = mod.extract_sizes(soup)
    return {
        "url": final_url or row["url"],
        "handle": row["handle"],
        "more_info": "",
        "title": title,
        "subtitle": "",
        "price": float(price),
        "body": mod.extract_body(soup),
        "categories_1": row["categories_1"],
        "categories_2": row["categories_2"],
        "categories_3": row["categories_3"],
        "option1_name": "Color" if color else "",
        "option1_value": color,
        "option2_name": "Size" if sizes else "",
        "option2_value": json.dumps(sizes, ensure_ascii=False) if sizes else "",
        "option3_name": "",
        "option3_value": "",
        "image_src": json.dumps(images, ensure_ascii=False),
        "size_price": "",
        "sole_id": row["sole_id"],
    }


def update_goods(conn, item, row_id):
    fields = [
        "url",
        "handle",
        "more_info",
        "title",
        "subtitle",
        "price",
        "body",
        "categories_1",
        "categories_2",
        "categories_3",
        "option1_name",
        "option1_value",
        "option2_name",
        "option2_value",
        "option3_name",
        "option3_value",
        "image_src",
        "size_price",
        "sole_id",
    ]
    sql = "update goods set " + ", ".join(f"{field}=?" for field in fields) + " where id=?"
    conn.execute(sql, [item.get(field) for field in fields] + [row_id])
    conn.commit()


def main():
    db_path = Path(os.environ.get("TEAMS_REPAIR_DB") or latest_db())
    limit = int(os.environ.get("TEAMS_REPAIR_LIMIT", "0") or 0)
    sleep_seconds = float(os.environ.get("TEAMS_REPAIR_SLEEP", "2") or 0)
    logger.info(f"11TEAMSPORTS repair db={db_path} limit={limit or 'all'}")

    mod = load_spider_module()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select * from goods
        where lower(coalesce(title,'')) like '%not a bot%'
           or lower(coalesce(body,'')) like '%not a bot%'
        order by id
        """
    ).fetchall()
    if limit:
        rows = rows[:limit]

    ok = 0
    failed = 0
    for index, row in enumerate(rows, 1):
        try:
            item = build_item(mod, row)
            update_goods(conn, item, row["id"])
            ok += 1
            logger.success(f"修复成功 {index}/{len(rows)} id={row['id']} title={item['title']} url={item['url']}")
        except Exception as exc:
            failed += 1
            logger.error(f"修复失败 {index}/{len(rows)} id={row['id']} url={row['url']} error={type(exc).__name__}: {exc}")
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    remain = conn.execute(
        "select count(*) from goods where lower(coalesce(title,'')) like '%not a bot%' or lower(coalesce(body,'')) like '%not a bot%'"
    ).fetchone()[0]
    logger.info(f"11TEAMSPORTS repair done ok={ok} failed={failed} remain_bot_rows={remain}")
    conn.close()


if __name__ == "__main__":
    main()


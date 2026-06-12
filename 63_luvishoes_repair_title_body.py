# -*- coding: utf-8 -*-
import glob
import importlib.util
import os
import re
import sqlite3
import time

from bs4 import BeautifulSoup


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "63_luvishoes.py")


def load_luvishoes():
    spec = importlib.util.spec_from_file_location("luvishoes_spider", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def latest_db():
    pattern = os.path.join(BASE_DIR, "goods", "*_63_luvishoes.db")
    paths = [
        path for path in glob.glob(pattern)
        if re.search(r"^\d+_63_luvishoes\.db$", os.path.basename(path))
    ]
    if not paths:
        raise FileNotFoundError("未找到 *_63_luvishoes.db")
    return max(paths, key=os.path.getmtime)


def bad_body(body):
    body = body or ""
    markers = (
        "(0)",
        "Havale ile Ödeme",
        "Kapıda Ödeme",
        "İade Seçenekleri",
        "Kargo &amp; Teslimat",
        "Kargo & Teslimat",
        "Ödeme Seçenekleri",
    )
    if any(marker in body for marker in markers):
        return True
    return "Ürün Özellikleri" not in body or "Ürün Kullanım Kılavuzu" not in body


def main():
    luv = load_luvishoes()
    db_path = latest_db()
    print(f"db={os.path.basename(db_path)}", flush=True)
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    read_cur = conn.cursor()
    write_cur = conn.cursor()
    read_cur.execute("SELECT COUNT(*) FROM goods")
    total_rows = read_cur.fetchone()[0]
    limit = int(os.environ.get("LUVISHOES_REPAIR_LIMIT", "0") or 0)
    commit_every = max(1, int(os.environ.get("LUVISHOES_REPAIR_COMMIT_EVERY", "50") or 50))
    print(f"total_rows={total_rows} limit={limit or 'ALL'}", flush=True)

    updated = 0
    skipped_cache = 0
    skipped_parse = 0
    parsed_by_url = {}
    scanned = 0
    started = time.time()

    read_cur.execute("SELECT id, url, title, body FROM goods ORDER BY id")
    while True:
        batch = read_cur.fetchmany(100)
        if not batch:
            break
        for row_id, url, title, body in batch:
            scanned += 1
            if limit and scanned > limit:
                break
            need_title = luv.clean_product_title(title) != (title or "")
            need_body = bad_body(body)
            if not need_title and not need_body:
                continue

            if url not in parsed_by_url:
                full_url = luv.normalize_url(url, luv.HOME_URL, keep_query=True)
                cache_path = luv._cache_file("detail", {"url": full_url})
                if not cache_path.exists():
                    parsed_by_url[url] = None
                else:
                    html = cache_path.read_text(encoding="utf-8", errors="ignore")
                    if luv.is_bad_html(html):
                        parsed_by_url[url] = None
                    else:
                        soup = BeautifulSoup(html, "html.parser")
                        parsed_by_url[url] = {
                            "title": luv.extract_title(soup, title),
                            "body": luv.extract_body(soup),
                        }

            parsed = parsed_by_url[url]
            if not parsed:
                skipped_cache += 1
                continue
            new_title = parsed.get("title") or luv.clean_product_title(title)
            new_body = parsed.get("body") or body
            if not new_title or not new_body:
                skipped_parse += 1
                continue
            write_cur.execute("UPDATE goods SET title=?, body=? WHERE id=?", (new_title, new_body, row_id))
            updated += 1

            if updated % commit_every == 0:
                conn.commit()
                print(
                    f"progress scanned={scanned}/{total_rows} updated={updated} "
                    f"skipped_cache={skipped_cache} skipped_parse={skipped_parse} "
                    f"elapsed={time.time() - started:.1f}s",
                    flush=True,
                )
            if scanned % 500 == 0:
                print(
                    f"scan scanned={scanned}/{total_rows} updated={updated} "
                    f"skipped_cache={skipped_cache} skipped_parse={skipped_parse} "
                    f"elapsed={time.time() - started:.1f}s",
                    flush=True,
                )
            if limit and scanned >= limit:
                break
        if limit and scanned >= limit:
            break

    conn.commit()
    read_cur.close()
    write_cur.close()
    check_cur = conn.cursor()
    check_cur.execute("SELECT COUNT(*) FROM goods WHERE title LIKE '%(%-%-%'")
    bad_titles_after = check_cur.fetchone()[0]
    bad_body_sample = 0
    check_cur.execute("SELECT body FROM goods ORDER BY id LIMIT 1000")
    for (body,) in check_cur.fetchall():
        if bad_body(body):
            bad_body_sample += 1
    check_cur.close()
    conn.close()
    print(f"updated={updated}", flush=True)
    print(f"skipped_cache={skipped_cache}", flush=True)
    print(f"skipped_parse={skipped_parse}", flush=True)
    print(f"bad_titles_after={bad_titles_after}", flush=True)
    print(f"bad_body_sample_first_1000={bad_body_sample}", flush=True)
    print(f"seconds={time.time() - started:.1f}", flush=True)


if __name__ == "__main__":
    main()

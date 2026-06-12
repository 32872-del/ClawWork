import argparse
import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR = ROOT / "out"


def latest_db_path():
    candidates = sorted(
        DEFAULT_DB_DIR.glob("*_4_lanidor.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def normalize_image_url(raw_url):
    if not raw_url:
        return ""

    url = str(raw_url).strip().replace("&amp;", "&")
    if not url or "blank_" in url or "placeholder" in url:
        return ""

    url = unquote(url)

    nested = re.search(
        r"(https?://www\.lanidor\.com/cdn-srcs/products/[^?\s\"'<>]+)",
        url,
    )
    if nested:
        url = nested.group(1)

    small_match = re.search(
        r"https?://bcdn\.lanidor\.com/products/cdn_small/(\d+)\.([a-zA-Z0-9]+)",
        url,
    )
    if small_match:
        return f"https://www.lanidor.com/cdn-srcs/products/{small_match.group(1)}.{small_match.group(2)}"

    if "/cdn-srcs/products/" in url:
        url = url.split("?", 1)[0]
        return re.sub(r"_(?:G|g)(\.[a-zA-Z0-9]+)$", r"\1", url)

    if "cdn.lanidor.com/Produtos/grandes/" in url:
        return url.split("?", 1)[0]

    return url.split("?", 1)[0]


def load_images(value):
    if not value:
        return []
    try:
        data = json.loads(value)
        if isinstance(data, list):
            return [str(x) for x in data if x]
        if isinstance(data, str):
            return [data]
    except json.JSONDecodeError:
        pass
    return [x.strip() for x in str(value).split(",") if x.strip()]


def repair_db(db_path, apply=False, backup=True):
    db_path = Path(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    rows = cur.execute("select id, image_src from goods").fetchall()
    changed_rows = 0
    changed_urls = 0
    total_urls = 0
    empty_after = 0
    examples = []

    updates = []
    for row_id, image_src in rows:
        old_images = load_images(image_src)
        new_images = []
        seen = set()

        for old_url in old_images:
            total_urls += 1
            new_url = normalize_image_url(old_url)
            if not new_url or new_url in seen:
                continue
            seen.add(new_url)
            new_images.append(new_url)
            if new_url != old_url:
                changed_urls += 1
                if len(examples) < 8:
                    examples.append((old_url, new_url))

        if not new_images:
            empty_after += 1
            new_value = "[]"
        else:
            new_value = json.dumps(new_images, ensure_ascii=False)

        if new_value != image_src:
            changed_rows += 1
            updates.append((new_value, row_id))

    backup_path = None
    if apply and updates:
        if backup:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.with_suffix(db_path.suffix + f".bak_{stamp}")
            shutil.copy2(db_path, backup_path)
        cur.executemany("update goods set image_src=? where id=?", updates)
        con.commit()

    con.close()
    return {
        "db": str(db_path),
        "rows": len(rows),
        "total_urls": total_urls,
        "changed_rows": changed_rows,
        "changed_urls": changed_urls,
        "empty_after": empty_after,
        "backup": str(backup_path) if backup_path else "",
        "examples": examples,
    }


def main():
    parser = argparse.ArgumentParser(description="Repair Lanidor product image URLs in goods SQLite DBs.")
    parser.add_argument("db", nargs="?", help="Database path. Defaults to the latest *_4_lanidor.db in out/.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this, only prints a dry-run report.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a .bak copy before writing.")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else latest_db_path()
    if not db_path:
        raise SystemExit("No *_4_lanidor.db files found in out/.")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}")
    result = repair_db(db_path, apply=args.apply, backup=not args.no_backup)
    print("\nDB:", result["db"])
    print("rows:", result["rows"])
    print("image urls:", result["total_urls"])
    print("changed rows:", result["changed_rows"])
    print("changed urls:", result["changed_urls"])
    print("empty rows after repair:", result["empty_after"])
    if result["backup"]:
        print("backup:", result["backup"])
    if result["examples"]:
        print("examples:")
        for old_url, new_url in result["examples"]:
            print("  -", old_url)
            print("    ->", new_url)


if __name__ == "__main__":
    main()

import argparse
import ast
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KRUIDVAT_DB = BASE_DIR / "goods" / "1780389264_50_kruidvat_cosimg_datawork1.db"
DEFAULT_KRUIDVAT_COS_DOMAIN = "https://datawork1-1438065526.cos.ap-guangzhou.myqcloud.com/kruidvat_1/"
DEFAULT_KRUIDVAT_EXISTING_DIR = BASE_DIR / "downloadimg" / "kruidvat_1"


def latest_db(pattern, fallback):
    candidates = []
    for folder in (BASE_DIR / "goods", BASE_DIR / "out"):
        candidates.extend(folder.glob(pattern))
    if not candidates:
        return Path(fallback)
    return max(candidates, key=lambda path: path.stat().st_mtime)


DEFAULT_SRC_DB = Path(os.environ.get("KRUIDVAT_COS_SRC_DB", DEFAULT_KRUIDVAT_DB))
DEFAULT_OUT_DB = Path(os.environ.get("KRUIDVAT_COS_OUT_DB", DEFAULT_SRC_DB))
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"}


def md5_text(value):
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def normalized_url(url):
    url = html.unescape(str(url or "").strip())
    if not url.startswith(("http://", "https://")):
        return ""
    return url


def suffix_from_url(url):
    path = unquote(urlsplit(url).path)
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return suffix
    return ".jpg"


def hash_input_without_suffix(url):
    parts = urlsplit(url)
    path = unquote(parts.path)
    suffix = Path(path).suffix
    if suffix:
        path = path[: -len(suffix)]
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def local_filename(url, prefix=""):
    url = normalized_url(url)
    if not url:
        return ""
    return f"{prefix}{md5_text(hash_input_without_suffix(url))}{suffix_from_url(url)}"


def is_kruidvat_media(url):
    parts = urlsplit(str(url or ""))
    return "kruidvat.nl" in parts.netloc.lower() and parts.path.startswith("/medias/")


def parse_image_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    for loader in (json.loads, ast.literal_eval):
        try:
            data = loader(text)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except Exception:
            pass
    return [item.strip() for item in text.split(",") if item.strip()]


def replace_image_src_value(value, prefix="", existing_dir=None):
    images = parse_image_list(value)
    if not images:
        return value
    replaced = []
    for url in images:
        if not is_kruidvat_media(url):
            replaced.append(url)
            continue
        filename = local_filename(url, prefix)
        if existing_dir is not None:
            local_name = local_filename(url)
            if not local_name or not (existing_dir / local_name).is_file():
                replaced.append(url)
                continue
        replaced.append(filename or url)
    return json.dumps(replaced, ensure_ascii=False)


def table_columns(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    cursor.close()
    return cols


def table_exists(conn, table_name):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone() is not None
    cursor.close()
    return exists


def rewrite_table(conn, table_name, prefix="", existing_dir=None):
    cols = table_columns(conn, table_name)

    select_cols = ["rowid"]
    if "image_src" in cols:
        select_cols.append("image_src")
    if len(select_cols) == 1:
        return 0

    cursor = conn.cursor()
    cursor.execute(f"SELECT {', '.join(select_cols)} FROM {table_name}")
    rows = cursor.fetchall()

    updated = 0
    for row in rows:
        data = dict(zip(select_cols, row))
        sets = []
        params = []

        if "image_src" in data:
            new_image_src = replace_image_src_value(data["image_src"], prefix, existing_dir=existing_dir)
            if new_image_src != data["image_src"]:
                sets.append("image_src=?")
                params.append(new_image_src)

        if sets:
            params.append(data["rowid"])
            cursor.execute(f"UPDATE {table_name} SET {', '.join(sets)} WHERE rowid=?", params)
            updated += 1

    conn.commit()
    cursor.close()
    return updated


def main():
    parser = argparse.ArgumentParser(description="Copy DB and replace image URLs with md5 filenames.")
    parser.add_argument("--src-db", default=str(DEFAULT_SRC_DB), help="source DB path")
    parser.add_argument("--out-db", default=str(DEFAULT_OUT_DB), help="new DB path")
    parser.add_argument("--prefix", default="", help="optional prefix before md5 filename, e.g. /uploads/vanaheim/")
    parser.add_argument("--domain", default=os.environ.get("KRUIDVAT_COS_DOMAIN", DEFAULT_KRUIDVAT_COS_DOMAIN), help="optional image domain, e.g. http://xxx or http://xxx/images")
    parser.add_argument("--existing-dir", default=os.environ.get("KRUIDVAT_COS_EXISTING_DIR", str(DEFAULT_KRUIDVAT_EXISTING_DIR)), help="only replace images whose md5 filename exists in this local directory")
    parser.add_argument("--overwrite", action="store_true", help="overwrite out DB if it exists")
    args = parser.parse_args()

    prefix = args.prefix
    if args.domain:
        prefix = args.domain.rstrip("/") + "/"
    existing_dir = Path(args.existing_dir) if args.existing_dir else None

    src_db = Path(args.src_db)
    out_db = Path(args.out_db)
    in_place = src_db.resolve() == out_db.resolve()
    if out_db.exists() and not in_place:
        if not args.overwrite:
            raise FileExistsError(f"Output DB already exists: {out_db}")
        out_db.unlink()
    out_db.parent.mkdir(parents=True, exist_ok=True)
    if not in_place:
        shutil.copy2(src_db, out_db)

    conn = sqlite3.connect(out_db)
    total = 0
    for table in ("goods", "liebiao", "zhuti", "bianti"):
        if table_exists(conn, table):
            count = rewrite_table(conn, table, prefix=prefix, existing_dir=existing_dir)
            total += count
            print(f"{table}: updated {count} rows")
    conn.close()

    print(f"Done. Source unchanged: {src_db}")
    print(f"New DB: {out_db}")
    print(f"Updated rows: {total}")


if __name__ == "__main__":
    main()

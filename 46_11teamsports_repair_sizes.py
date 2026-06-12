# -*- coding: utf-8 -*-
import ast
import json
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path

from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)


def latest_db():
    files = sorted((BASE_DIR / "goods").glob("*_46_11teamsports.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("未找到 *_46_11teamsports.db")
    return files[0]


def parse_sizes(value):
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [str(value)]


def normalize_size(value):
    text = " ".join(str(value or "").split()).strip()
    replacements = {
        "½": "1/2",
        "⅓": "1/3",
        "⅔": "2/3",
        "&#189;": "1/2",
        "&#8531;": "1/3",
        "&#8532;": "2/3",
        "陆": "1/2",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+EU(?:\s|$).*", "", text, flags=re.I)
    text = re.sub(r"(\d)(1/2|1/3|2/3)$", r"\1 \2", text)
    return text.strip()


def comparable_size(value):
    text = normalize_size(value)
    text = re.sub(r"^(?:Children'?s|Kids|Junior)\s+", "", text, flags=re.I)
    return text.lower()


def clean_sizes(sizes):
    result = []
    seen = set()
    for size in sizes:
        cleaned = normalize_size(size)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def keep_first_size_round(sizes):
    size_count = len(sizes)
    if size_count >= 2 and size_count % 2 == 0:
        half = size_count // 2
        first = sizes[:half]
        second = sizes[half:]
        if [comparable_size(item) for item in first] == [comparable_size(item) for item in second]:
            return clean_sizes(first)
    return clean_sizes(sizes)


def has_duplicate_round(sizes):
    if len(sizes) < 2 or len(sizes) % 2 != 0:
        return False
    half = len(sizes) // 2
    first = [comparable_size(item) for item in sizes[:half]]
    second = [comparable_size(item) for item in sizes[half:]]
    return first == second


def main():
    db_path = Path(os.environ.get("TEAMS_SIZE_REPAIR_DB") or latest_db())
    dry_run = os.environ.get("TEAMS_SIZE_REPAIR_DRY_RUN", "0") == "1"
    backup = os.environ.get("TEAMS_SIZE_REPAIR_BACKUP", "1") == "1"
    logger.info(f"11TEAMSPORTS size repair db={db_path} dry_run={dry_run}")

    if backup and not dry_run:
        backup_path = db_path.with_suffix(db_path.suffix + f".sizebak_{int(time.time())}")
        shutil.copy2(db_path, backup_path)
        logger.info(f"已备份数据库: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("select id, url, title, option2_name, option2_value from goods where option2_name='Size'").fetchall()
    changed = []
    for row in rows:
        sizes = parse_sizes(row["option2_value"])
        if not has_duplicate_round(sizes):
            continue
        cleaned = keep_first_size_round(sizes)
        if cleaned == sizes:
            continue
        changed.append((row, sizes, cleaned))

    logger.info(f"检测到前后两轮重复尺码行数: {len(changed)}")
    for row, old, new in changed[:20]:
        logger.info(f"id={row['id']} {row['title']} {len(old)} -> {len(new)} old={old[:8]} new={new[:8]}")

    if not dry_run:
        for row, _old, new in changed:
            conn.execute(
                "update goods set option2_value=? where id=?",
                (json.dumps(new, ensure_ascii=False) if new else "", row["id"]),
            )
        conn.commit()

    remain = 0
    for row in conn.execute("select option2_value from goods where option2_name='Size'"):
        sizes = parse_sizes(row["option2_value"])
        if has_duplicate_round(sizes):
            remain += 1
    logger.info(f"11TEAMSPORTS size repair done changed={0 if dry_run else len(changed)} remain_duplicate_round={remain}")
    conn.close()


if __name__ == "__main__":
    main()

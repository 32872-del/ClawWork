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


def parse_images(value):
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [str(value)]


def normalize_image(url, size=480):
    return re.sub(r"-(?:120|480|960)(\.webp)(?:$|\?)", rf"-{size}\1", str(url or ""))


def main():
    db_path = Path(os.environ.get("TEAMS_IMAGE_REPAIR_DB") or latest_db())
    target_size = int(os.environ.get("TEAMS_IMAGE_SIZE", "480") or 480)
    dry_run = os.environ.get("TEAMS_IMAGE_REPAIR_DRY_RUN", "0") == "1"
    backup = os.environ.get("TEAMS_IMAGE_REPAIR_BACKUP", "1") == "1"
    logger.info(f"11TEAMSPORTS image repair db={db_path} target_size={target_size} dry_run={dry_run}")

    if backup and not dry_run:
        backup_path = db_path.with_suffix(db_path.suffix + f".imagebak_{int(time.time())}")
        shutil.copy2(db_path, backup_path)
        logger.info(f"已备份数据库: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("select id, image_src from goods").fetchall()
    changed = 0
    sample = []
    for row in rows:
        images = parse_images(row["image_src"])
        new_images = [normalize_image(url, target_size) for url in images]
        if new_images == images:
            continue
        changed += 1
        if len(sample) < 10:
            sample.append((row["id"], images[:2], new_images[:2]))
        if not dry_run:
            conn.execute("update goods set image_src=? where id=?", (json.dumps(new_images, ensure_ascii=False), row["id"]))
    if not dry_run:
        conn.commit()

    logger.info(f"需要更新图片行数: {changed}")
    for item in sample:
        logger.info(f"id={item[0]} old={item[1]} new={item[2]}")
    conn.close()


if __name__ == "__main__":
    main()


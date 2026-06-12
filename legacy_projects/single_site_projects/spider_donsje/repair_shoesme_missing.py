import glob
import importlib.util
import os
import sqlite3
import sys
import time
from copy import deepcopy

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

for key, value in {
    "PYTHONUNBUFFERED": "1",
    "SHOESME_BOT_HEADLESS": "0",
    "SHOESME_BOT_BATCH": "1",
    "SHOESME_BOT_WAIT": "5",
    "SHOESME_BOT_CACHE": "1",
    "SHOESME_GOODS_FIRST": "1",
}.items():
    os.environ.setdefault(key, value)

MODULE_PATH = os.path.join(BASE_DIR, "3_shoesme_botasaurus.py")


def load_runner():
    spec = importlib.util.spec_from_file_location("shoesme_runner", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()


def latest_db_path():
    override = os.environ.get("SHOESME_DB_PATH")
    if override and os.path.exists(override):
        return override
    candidates = glob.glob(os.path.join(BASE_DIR, "goods", "*_3_shoesme_botasaurus.db"))
    if not candidates:
        return None
    return sorted(candidates, key=os.path.getmtime, reverse=True)[0]


def flatten_categories(data, item=None, depth=1):
    item = dict(item or {})
    for name, value in data.items():
        current = dict(item)
        current[f"categories_{depth}"] = str(name).strip()
        if isinstance(value, dict):
            yield from flatten_categories(value, current, depth + 1)
        else:
            current["url"] = value
            current["page"] = 1
            current["task_type"] = "flat_task"
            yield current


def build_missing_tasks(db):
    payload = runner.load_base_module().get_shoesme_payload_list()
    tasks = list(flatten_categories(payload))
    missing = []
    for task in tasks:
        c1 = task.get("categories_1") or ""
        c2 = task.get("categories_2") or ""
        c3 = task.get("categories_3") or ""
        count = db.cursor.execute(
            'select count(*) from goods where categories_1=? and ifnull(categories_2,"")=? and ifnull(categories_3,"")=?',
            (c1, c2, c3),
        ).fetchone()[0]
        if count == 0:
            missing.append(task)
    return missing


def save_records(db, records):
    return runner.save_records(db, records)


def main():
    db_path = latest_db_path()
    if not db_path:
        raise FileNotFoundError("No Shoesme DB found under goods/")

    print(f"[repair] using db: {db_path}", flush=True)
    db = runner.OperateDB(db_path)
    try:
        missing = build_missing_tasks(db)
        print(f"[repair] missing leaf categories: {len(missing)}", flush=True)
        for task in missing[:20]:
            print(f"  - {task.get('categories_1')} / {task.get('categories_2')} / {task.get('categories_3') or ''} -> {task['url']}", flush=True)

        flat_tasks = deepcopy(missing)
        goods_tasks = []
        saved_count = 0
        empty_rounds = 0

        while flat_tasks or goods_tasks:
            batch = []
            source = None
            if goods_tasks:
                source = "goods"
                batch = goods_tasks[:1]
                del goods_tasks[:1]
            elif flat_tasks:
                source = "flat"
                batch = flat_tasks[:1]
                del flat_tasks[:1]

            if not batch:
                empty_rounds += 1
                if empty_rounds > 10:
                    break
                time.sleep(5)
                continue

            print(f"[repair-batch] {source} remaining flat={len(flat_tasks)} goods={len(goods_tasks)}", flush=True)
            results = runner.scrape_task(batch)
            if isinstance(results, dict):
                results = [results]

            for item in results or []:
                flat_tasks.extend(item.get("flat_tasks") or [])
                goods_tasks.extend(item.get("goods_tasks") or [])
                for retry_task in item.get("retry_tasks") or []:
                    if retry_task.get("task_type") == "flat_task":
                        flat_tasks.append(retry_task)
                    else:
                        goods_tasks.append(retry_task)
                saved_count += save_records(db, item.get("records") or [])

        print(f"[repair-done] saved={saved_count} db={db.path}", flush=True)
    finally:
        db.close_data()
        try:
            runner.scrape_task.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

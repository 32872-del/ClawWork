import argparse
import json
import sqlite3


def build_category_tree(db_path, table_name="goods"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT handle, categories_1, categories_2, categories_3
        FROM {table_name}
    """)
    rows = cursor.fetchall()
    conn.close()

    seen = set()
    tree = {}

    for handle, c1, c2, c3 in rows:
        handle_prefix = (handle or "").split("_")[0]
        if handle_prefix in seen:
            continue
        seen.add(handle_prefix)

        c1 = (c1 or "").strip()
        c2 = (c2 or "").strip()
        c3 = (c3 or "").strip()

        if c1 and not c2:
            tree[c1] = tree.get(c1, 0) + 1
            continue

        if c1 not in tree or isinstance(tree[c1], int):
            tree[c1] = {}

        if c2 and not c3:
            tree[c1][c2] = tree[c1].get(c2, 0) + 1
            continue

        if c2 not in tree[c1] or isinstance(tree[c1][c2], int):
            tree[c1][c2] = {}

        tree[c1][c2][c3] = tree[c1][c2].get(c3, 0) + 1

    return tree


def main():
    parser = argparse.ArgumentParser(description="统计 goods 表中按 handle 去重后的目录层级数量")
    parser.add_argument("db_path", help="SQLite 数据库路径")
    parser.add_argument("--table", default="goods", help="表名，默认 goods")
    args = parser.parse_args()

    tree = build_category_tree(args.db_path, args.table)
    print(json.dumps(tree, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()

import sqlite3
import json

db_path = r"E:\Frame\spider\out\1779186049_45_kiko milano.db"
table_name = "goods"

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

    # 只有一级
    if c1 and not c2:

        if c1 not in tree:
            tree[c1] = 0

        tree[c1] += 1
        continue

    # 一级不存在
    if c1 not in tree or isinstance(tree[c1], int):
        tree[c1] = {}

    # 只有二级
    if c2 and not c3:

        if c2 not in tree[c1]:
            tree[c1][c2] = 0

        tree[c1][c2] += 1
        continue

    # 有三级
    if c2 not in tree[c1] or isinstance(tree[c1][c2], int):
        tree[c1][c2] = {}

    if c3 not in tree[c1][c2]:
        tree[c1][c2][c3] = 0

    tree[c1][c2][c3] += 1


print(json.dumps(tree, ensure_ascii=False, indent=4))
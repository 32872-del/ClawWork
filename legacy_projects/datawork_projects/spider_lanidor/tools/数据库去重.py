import pandas as pd
import sqlite3
import csv  # 保留（虽然现在用不到，但你原代码有）

name = '1777448557_4_lanidor.db'

# 输入 / 输出
input_db = rf"..\goods\{name}"
output_db = rf"..\out\{name}"

# 一个商品链接里面有多种颜色，没有跳转，全部颜色公用图片
flag = False
# flag = True

try:
    # ================== 读取 DB ==================
    conn = sqlite3.connect(input_db)

    # ⚠️ 改成你真实的表名
    table_name = "goods"

    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()

    print(f"成功读取数据库，共 {len(df)} 行")

    # ================== 数据清洗 ==================
    print("\n第一步：删除不符合条件的数据...")
    before_dropna = len(df)

    df_cleaned = df.dropna(subset=["title", "price", "image_src"], how="any")

    deleted_empty = before_dropna - len(df_cleaned)
    print(f"  删除空值行 {deleted_empty} 行，剩余 {len(df_cleaned)} 行")

    before_filter = len(df_cleaned)

    df_cleaned = df_cleaned[df_cleaned['image_src'].astype(str).str.strip() != '[]']

    deleted_empty_list = before_filter - len(df_cleaned)
    print(f"  删除 image_src 为空列表（[]）的行 {deleted_empty_list} 行，剩余 {len(df_cleaned)} 行")

    # ================== 排序 ==================
    print("\n第二步：按 handle 字段排序...")

    df_sorted = df_cleaned.sort_values(by="handle", ascending=True).reset_index(drop=True)

    print(f"  排序完成，共 {len(df_sorted)} 行")

    # ================== 去重 ==================
    print("\n第三步：执行去重操作...")

    if flag:
        duplicate_cols = [
            "title", "price", "categories_1", "categories_2",
            "categories_3", "image_src", "option1_value", "option2_value"
        ]
    else:
        duplicate_cols = [
            "title", "price", "categories_1",
            "categories_2", "categories_3", "image_src"
        ]

    before_dedup = len(df_sorted)

    df_deduped = df_sorted.drop_duplicates(subset=duplicate_cols, keep="first")

    deleted_duplicates = before_dedup - len(df_deduped)

    print(f"  删除重复数据 {deleted_duplicates} 行，剩余 {len(df_deduped)} 行")

    # ================== 写入 DB ==================
    conn_out = sqlite3.connect(output_db)

    table_name_out = "goods"  # 输出表名

    df_deduped.to_sql(
        table_name_out,
        conn_out,
        if_exists='replace',
        index=False
    )

    conn_out.close()

    # ================== 输出统计 ==================
    print("\n" + "=" * 50)
    print(f"处理完成！")
    print(f"原始数据: {len(df)} 行")
    print(f"删除空值: {deleted_empty} 行")
    print(f"删除空列表: {deleted_empty_list} 行")
    print(f"删除重复: {deleted_duplicates} 行")
    print(f"最终结果: {len(df_deduped)} 行")
    print(f"文件已保存到: {output_db} （表: {table_name_out}）")
    print("=" * 50)

# ================== 异常处理 ==================
except FileNotFoundError:
    print(f"错误：找不到数据库文件 {input_db}，请检查路径！")

except Exception as e:
    print(f"处理过程中出错：{str(e)}")
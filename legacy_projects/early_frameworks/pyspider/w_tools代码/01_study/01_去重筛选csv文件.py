import pandas as pd

input_csv = r"E:\Frame\Frame\pyspider\goods\2026-02-25 15-02-34_prosto.csv"
output_csv = r"E:\Frame\Frame\pyspider\good2\prosto.csv"
# -------------------------------------------------------------------

try:
    try:
        df = pd.read_csv(input_csv, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv, encoding="gbk")
    print(f"成功读取文件，原始数据共 {len(df)} 行")
    print("\n第一步：删除不符合条件的数据...")
    before_dropna = len(df)
    df_cleaned = df.dropna(subset=["title", "price", "image_src"], how="any")
    deleted_empty = before_dropna - len(df_cleaned)
    print(f"  删除空值行 {deleted_empty} 行，剩余 {len(df_cleaned)} 行")

    before_filter = len(df_cleaned)
    df_cleaned = df_cleaned[df_cleaned['image_src'].str.strip() != '[]']
    deleted_empty_list = before_filter - len(df_cleaned)
    print(f"  删除 image_src 为空列表（[]）的行 {deleted_empty_list} 行，剩余 {len(df_cleaned)} 行")

    # 第二步：按 handle 字段排序
    print("\n第二步：按 handle 字段排序...")
    df_sorted = df_cleaned.sort_values(by="handle", ascending=True).reset_index(drop=True)
    print(f"  排序完成，共 {len(df_sorted)} 行")

    print("\n第三步：执行去重操作...")
    duplicate_cols = ["title", "price", "categories_1", "categories_2", "categories_3", "image_src"]
    # duplicate_cols = ["title", "price", "categories_1", "categories_2", "categories_3", "image_src",
    #                   "option1_value", "option2_value"]

    before_dedup = len(df_sorted)
    df_deduped = df_sorted.drop_duplicates(subset=duplicate_cols, keep="first")
    deleted_duplicates = before_dedup - len(df_deduped)
    print(f"  删除重复数据 {deleted_duplicates} 行，剩余 {len(df_deduped)} 行")
    df_deduped.to_csv(output_csv, encoding="utf-8", index=False)

    print("\n" + "=" * 50)
    print(f"处理完成！")
    print(f"原始数据: {len(df)} 行")
    print(f"删除空值: {deleted_empty} 行")
    print(f"删除空列表: {deleted_empty_list} 行")
    print(f"删除重复: {deleted_duplicates} 行")
    print(f"最终结果: {len(df_deduped)} 行")
    print(f"文件已保存到: {output_csv}")
    print("=" * 50)

except FileNotFoundError:
    print(f"错误：找不到文件 {input_csv}，请检查文件路径是否正确！")
except Exception as e:
    print(f"处理过程中出错：{str(e)}")
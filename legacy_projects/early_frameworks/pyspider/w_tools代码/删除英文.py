import pandas as pd
import ast  # 用于安全地解析字符串形式的列表

# 读取CSV文件
df = pd.read_csv(r'E:\Frame\Frame\pyspider\good2\cleaned_bogner2_final.csv')

# 指定要清理的列名
column_to_clean = 'option2_value'


def clean_option_value(value):
    """
    清理option2_value列，删除不需要的文本
    """
    if pd.isna(value):
        return value

    try:
        # 安全地解析字符串形式的列表
        value_str = str(value)

        # 如果已经是列表，直接使用
        if isinstance(value, list):
            item_list = value
        else:
            # 解析字符串形式的列表
            item_list = ast.literal_eval(value_str)

        # 过滤掉不需要的项目 - 添加你要删除的所有项
        items_to_remove = [
            'Notify me', 'Add to bag', 'notify me', 'add to bag',
            'NOTIFY ME', 'ADD TO BAG', 'rozmiar uniwersalny',
            "Men's Team", "Women's Team",
            'Sold out (email when available)', 'Low stock',
            'Sold out', 'Out of stock', 'Email when available',
            'sold out (email when available)', 'low stock'  # 小写版本
        ]

        cleaned_list = [item for item in item_list if item not in items_to_remove]

        # 如果清理后列表为空，返回None（在CSV中会变成空值）
        if not cleaned_list:
            return None

        # 返回列表的字符串表示
        return str(cleaned_list)

    except (ValueError, SyntaxError):
        # 如果解析失败，尝试直接处理字符串
        value_str = str(value)

        # 删除所有不需要的文本（包括括号内的）
        texts_to_remove = [
            "'Sold out (email when available)'",
            "'Low stock'",
            "'Sold out'",
            "'Out of stock'",
            "'Notify me'",
            "'Add to bag'"
        ]

        for text in texts_to_remove:
            value_str = value_str.replace(text, '')

        # 处理不带引号的版本
        texts_to_remove_no_quotes = [
            "Sold out (email when available)",
            "Low stock",
            "Sold out",
            "Out of stock",
            "Notify me",
            "Add to bag"
        ]

        for text in texts_to_remove_no_quotes:
            value_str = value_str.replace(text, '')

        # 清理格式
        # 移除空字符串元素
        value_str = value_str.replace("' '", "', '")
        value_str = value_str.replace("', ',", "', '")
        value_str = value_str.replace(", ,", ",")
        value_str = value_str.replace(", ]", "]")
        value_str = value_str.replace("[, ", "[")
        value_str = value_str.replace("[ ,", "[")
        value_str = value_str.replace(", , ", ", ")

        # 移除多余的逗号
        while ",," in value_str:
            value_str = value_str.replace(",,", ",")

        # 清理空列表
        if value_str.strip() in ["[]", "['']", "[' ']", "[ '']", "['' ]"]:
            return None

        # 如果最终结果是空列表，返回None
        if not value_str.strip() or value_str.strip() == "[]":
            return None

        return value_str


# 应用清理函数
print("开始清理数据...")
df[column_to_clean] = df[column_to_clean].apply(clean_option_value)

# 显示清理前后对比
print("\n=== 清理前后对比示例 ===")
print("清理前（前5行）:")
sample_data = pd.read_csv(r'E:\Frame\Frame\pyspider\good2\cleaned_bogner2_final.csv')
for i in range(5):
    print(f"行{i}: {sample_data[column_to_clean].iloc[i]}")

print("\n清理后（前5行）:")
for i in range(5):
    print(f"行{i}: {df[column_to_clean].iloc[i]}")

# 显示更多示例，特别是包含'Sold out'或'Low stock'的行
print("\n=== 特殊示例（包含Sold out或Low stock的清理）===")
sample_data = pd.read_csv(r'E:\Frame\Frame\pyspider\good2\cleaned_bogner2_final.csv')
for i in range(min(10, len(df))):
    original_value = str(sample_data[column_to_clean].iloc[i])
    if "'Sold out" in original_value or "'Low stock" in original_value:
        print(f"行{i}:")
        print(f"  清理前: {original_value}")
        print(f"  清理后: {df[column_to_clean].iloc[i]}")
        print()

# 保存结果
output_file = r'E:\Frame\Frame\pyspider\good2\cleaned_bogner3_final.csv'
df.to_csv(output_file, index=False)
print(f"\n清理完成！文件已保存为: {output_file}")

# 验证清理结果
print("\n=== 清理结果验证 ===")
search_terms = [
    'Notify me', 'Add to bag', 'Sold out', 'Low stock',
    'Out of stock', 'Email when available'
]

for term in search_terms:
    count = df[column_to_clean].astype(str).str.contains(term, case=False, na=False).sum()
    print(f"包含 '{term}' 的行数: {count}")

# 显示空值统计
print(f"\n空值统计:")
print(f"空值数量: {df[column_to_clean].isna().sum()}")
print(f"空值占比: {df[column_to_clean].isna().mean():.2%}")

# 显示清理后的唯一值示例
print("\n清理后的前10个非空唯一值:")
unique_values = df[column_to_clean].dropna().unique()[:10]
for i, val in enumerate(unique_values):
    print(f"{i}: {val}")
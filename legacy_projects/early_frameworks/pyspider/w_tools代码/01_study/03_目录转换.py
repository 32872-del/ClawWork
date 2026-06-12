import json

start_data = {
        "New": "https://prosto.com/mezczyzna/nowosci",
        "Men": {
            "Mężczyzna": {
                "Nowości": "https://prosto.com/mezczyzna/nowosci",
                "Kurtki": "https://prosto.com/mezczyzna/kurtki",
                "Czapki": "https://prosto.com/mezczyzna/akcesoria/czapki",
                "Bluzy": "https://prosto.com/mezczyzna/bluzy",
                "Spodnie": "https://prosto.com/mezczyzna/spodnie",
                "Koszulki": "https://prosto.com/mezczyzna/koszulki",
                "Akcesoria": "https://prosto.com/mezczyzna/akcesoria",
                "Koszule": "https://prosto.com/mezczyzna/koszule",
                "Longsleeve": "https://prosto.com/mezczyzna/koszulki/longsleeve",
                "Szorty": "https://prosto.com/mezczyzna/spodenki",
                "Sale": "https://prosto.com/sale/mezczyzna",
            },
        },
        "Women": {
            "Kobieta": {
                "Kurtki": "https://prosto.com/kobieta/kurtki",
                "Koszulki": "https://prosto.com/kobieta/koszulki",
                "Koszule": "https://prosto.com/kobieta/koszule",
                "Longsleeve": "https://prosto.com/catalog/category/view/s/longsleeve/id/23/",
                "Bluzy": "https://prosto.com/kobieta/bluzy",
                "Spodnie": "https://prosto.com/kobieta/spodnie",
                "Czapki": "https://prosto.com/kobieta/czapki",
                "Akcesoria": "https://prosto.com/kobieta/akcesoria",
                "Sale": "https://prosto.com/sale/kobieta",
            },
        },
        "Kids": "https://prosto.com/dziecko",
        "Label": {
            "Sklep": {
                "Wszystko": "https://prosto.com/label",
                "Muzyka": "https://prosto.com/label/muzyka",
                "Książki": "https://prosto.com/label/ksiazki",
                "Merch": "https://prosto.com/label/merch",
            },
            "Artyści": {
                "Wszystko": "https://prosto.com/label",
                "Wojtek Sokół": "https://prosto.com/wojteksokol",
            },
        },

    }


def normalize_keys(data):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # 1. 去除首尾空格
            # 2. 将多个连续空格替换为单个空格
            # 3. 将逗号替换为斜杠（注意保留空格）
            # 4. 将首字母转为大写
            key = str(key).strip()
            key = ' '.join(key.split())  # 处理多余空格

            # 替换逗号为斜杠（考虑可能的不同格式）
            if ',' in key:
                key = key.replace(',', ' /')

            # 将每个单词的首字母转为大写（保持葡萄牙语特殊字符）
            words = key.split()
            capitalized_words = []
            for word in words:
                if word:  # 确保单词不为空
                    # 保持特殊字符如 + 号不变
                    if word in ['+', '/', '&', '-']:
                        capitalized_words.append(word)
                    else:
                        # 首字母大写，其余保持原样
                        capitalized_words.append(word[0].upper() + word[1:] if len(word) > 0 else word)

            new_key = ' '.join(capitalized_words)

            # 递归处理值（保留原顺序）
            new_dict[new_key] = normalize_keys(value)
        return new_dict
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        return data


def normalize_json_structure(data):
    """标准化整个JSON数据结构"""
    # 处理键名（保留原顺序）
    normalized = normalize_keys(data)

    # 检查并确保所有URL值是字符串
    def ensure_string_values(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith('http'):
                    # URL已经是字符串，保持不变
                    continue
                elif isinstance(value, dict):
                    ensure_string_values(value)
                elif isinstance(value, list):
                    for item in value:
                        ensure_string_values(item)
        return obj

    return ensure_string_values(normalized)


# 处理数据
processed_data = normalize_json_structure(start_data)

# 保存到文件（移除sort_keys=True，保留原顺序）
with open('02_data.json', 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, indent=4, ensure_ascii=False)  # 关键修改：删除sort_keys=True

print("处理完成！已生成合法的JSON数据（保留原字典顺序）。")
print(f"文件已保存为: 02_data.txt")
print(f"顶层键: {list(processed_data.keys())}")


# 修正的显示函数 - 安全地显示处理结果
def display_sample(data, max_items=2, max_subitems=2, indent=0):
    """安全地显示数据结构样本"""
    if isinstance(data, dict):
        items = list(data.items())[:max_items]
        for i, (key, value) in enumerate(items):
            prefix = "  " * indent
            print(f"{prefix}- {key}:")

            if isinstance(value, dict):
                # 递归显示子字典
                display_sample(value, max_subitems, max_subitems, indent + 1)
            elif isinstance(value, str):
                # 显示字符串值（特别是URL）
                if value.startswith('http'):
                    print(f"{prefix}  URL: {value[:50]}...")
                else:
                    print(f"{prefix}  Value: {value[:50]}...")
            else:
                print(f"{prefix}  Type: {type(value).__name__}")
    else:
        # 如果不是字典，直接显示
        print(f"{'  ' * indent}{data}")


print("\n示例处理结果:")
display_sample(processed_data, max_items=3)

# 或者使用更简单的方法检查前几个顶级项目
print("\n前3个顶级项目的详细内容:")
for i, (key, value) in enumerate(list(processed_data.items())[:3]):
    print(f"\n{i + 1}. {key}:")
    if isinstance(value, dict):
        print(f"   类型: 字典 (包含 {len(value)} 个子项)")
        # 显示子项
        for subkey, subvalue in list(value.items())[:2]:
            print(f"   - {subkey}:")
            if isinstance(subvalue, str):
                print(f"      URL: {subvalue[:50]}...")
    elif isinstance(value, str):
        print(f"   类型: 字符串 (URL)")
        print(f"   URL: {value}")
    else:
        print(f"   类型: {type(value).__name__}")
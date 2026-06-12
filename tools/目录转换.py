import json

start_data ={
    "الاعلى مبيعاً": "https://lomar.sa/categories/1523808/الاعلى-مبيعا",
    "ثوب وسديري": {
        "ثياب تفصيل": "https://lomar.sa/categories/1459273/ثياب-تفصيل",
        "ثياب جاهزة": "https://lomar.sa/categories/1459256/ثياب-جاهزة",
        "سديري": "https://lomar.sa/categories/1459258/سديري",
    },
    "الاكسسوارات": {
        "سبح": "https://lomar.sa/categories/1555583/سبح",
        "كبكات": "https://lomar.sa/categories/1555585/كبكات",
        "كيس غسيل": "https://lomar.sa/categories/1555586/كيس-غسيل",
    },
    "الشنط والمحافظ": "https://lomar.sa/categories/1555584/الشنط-والمحافظ",
    "كاجوال": {
        "سروال": "https://lomar.sa/categories/1555568/cserwal",
        "تيشيرت": "https://lomar.sa/categories/1555559/تيشيرت",
        "كابات": "https://lomar.sa/categories/1459252/كابات",
    },
    "الملابس الداخلية والجوارب": {
        "تيشيرت داخلي": "https://lomar.sa/categories/1555575/تيشيرت-داخلي",
        "بوكسر": "https://lomar.sa/categories/1555576/بوكسر",
        "سروال طويل": "https://lomar.sa/categories/1555577/سروال",
        "بجامة": "https://lomar.sa/categories/1555578/بجامة",
        "جوارب": "https://lomar.sa/categories/1555579/جوارب",
    },
    "العمرة": {
        "الحقائب": "https://lomar.sa/categories/1459272/الحقائب",
        "أحرام": "https://lomar.sa/categories/1459250/أحرام",
    },
    "احذية": "https://lomar.sa/categories/1459237/احذية",
    "الأشمغة": "https://lomar.sa/categories/1459233/الأشمغة",
    "العطور": "https://lomar.sa/categories/1459251/العطور",
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
with open('../0000_data.json', 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, indent=4, ensure_ascii=False)  # 关键修改：删除sort_keys=True

print("处理完成！已生成合法的JSON数据（保留原字典顺序）。")
print(f"文件已保存为: 02_data.json")
print(f"顶层键: {list(processed_data.keys())}")

# 显示部分处理结果作为示例
# print("\n示例处理结果:")
# for category, subcategories in list(processed_data.items())[:2]:
#     print(f"\n{category}:")
#     for subcat, items in list(subcategories.items())[:2]:
#         print(f"  - {subcat}:")
#         if isinstance(items, dict):
#             for item, url in list(items.items())[:2]:
#                 print(f"    * {item}: {url[:50]}...")
#         else:
#             print(f"    * URL: {items[:50]}...")
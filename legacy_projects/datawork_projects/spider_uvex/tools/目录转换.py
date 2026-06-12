import json

start_data = {
            "Kaski rowerowe": {
                "Allround": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-allround/",
                "City": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-city/",
                "Junior": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-junior/",
                "Mountainbike": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-mountainbike/",
                "Performance": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-performance/",
            },
            "Okulary": {
                "Allround": "https://uvex.com.pl/produkty/okulary/okulary-allround/",
                "Colorvision": "https://uvex.com.pl/produkty/okulary/okulary-colorvision/",
                "Fashion": "https://uvex.com.pl/produkty/okulary/okulary-fashion/",
                "Junior": "https://uvex.com.pl/produkty/okulary/okulary-junior/",
                "Polavision": "https://uvex.com.pl/produkty/okulary/okulary-polavision/",
                "Variomatic": "https://uvex.com.pl/produkty/okulary/okulary-variomatic/",
                "Z wymiennymi szybami": "https://uvex.com.pl/produkty/okulary/okulary-z-wymiennymi-szybami/",
            },
            "Kaski narciarskie": {
                "Allround": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-allround/",
                "Junior": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-junior/",
                "Performance": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-performance/",
                "Visor": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-visor/",
            },
            "Gogle": {
                "Allround": "https://uvex.com.pl/produkty/gogle/gogle-allround/",
                "Attract": "https://uvex.com.pl/produkty/gogle/gogle-attract/",
                "Colorvision": "https://uvex.com.pl/produkty/gogle/gogle-colorvision/",
                "Junior": "https://uvex.com.pl/produkty/gogle/gogle-junior/",
                "Race": "https://uvex.com.pl/produkty/gogle/gogle-race/",
                "Take Off": "https://uvex.com.pl/produkty/gogle/gogle-take-off/",
                "Variomatic": "https://uvex.com.pl/produkty/gogle/gogle-variomatic/",
            },
            "Akcesoria": {
                "Do gogli": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-gogli/",
                "Do kasków narciarskich": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-kaskow-narciarskich/",
                "Do kasków rowerowych": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-kaskow-rowerowych/",
                "Do okularów": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-okularow/",
                "Pozostałe": "https://uvex.com.pl/produkty/akcesoria/pozostale/",
            },
            "Outlet": "https://uvex.com.pl/produkty/outlet/",
            "Uvex Kid 4": "https://uvex.com.pl/produkty/uvex-kid-4/",
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
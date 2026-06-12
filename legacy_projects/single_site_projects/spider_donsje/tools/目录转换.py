import json

start_data = {
        "Nieuw": "https://www.shoesme.nl/nieuw",
        "Kinderen": {
            "Nieuw": "https://www.shoesme.nl/kinderschoenen/new-arrivals",
            "Zomerschoenen": "https://www.shoesme.nl/kinderschoenen/zomerschoenen",
            "Babyschoenen": "https://www.shoesme.nl/kinderschoenen/babyschoenen",
            "Peuterschoenen": "https://www.shoesme.nl/kinderschoenen/peuterschoenen",
            "Sandalen": "https://www.shoesme.nl/kinderschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/kinderschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/kinderschoenen/waterschoenen",
            "Buitenspeel schoenen": "https://www.shoesme.nl/kinderschoenen/buitenspeel-schoenen",
            "Shoesme only": "https://www.shoesme.nl/kinderschoenen/shoesme-only",
            "Gymschoenen": "https://www.shoesme.nl/kinderschoenen/gymschoenen",
            "Bikerboots": "https://www.shoesme.nl/kinderschoenen/bikerboots",
            "Kinderlaarzen": "https://www.shoesme.nl/kinderschoenen/kinderlaarzen",
            "Cowboylaarzen": "https://www.shoesme.nl/kinderschoenen/cowboylaarzen",
            "Lage schoenen": "https://www.shoesme.nl/kinderschoenen/lage-schoenen",
            "Hoge schoenen": "https://www.shoesme.nl/kinderschoenen/hoge-schoenen",
            "Klittenband schoenen": "https://www.shoesme.nl/kinderschoenen/klittenband-schoenen",
            "Brede kinderschoenen": "https://www.shoesme.nl/kinderschoenen/brede-kinderschoenen",
            "Winterschoenen": "https://www.shoesme.nl/kinderschoenen/winterschoenen",
            "Water-Proof": "https://www.shoesme.nl/kinderschoenen/water-proof",
            "Regenlaarzen": "https://www.shoesme.nl/kinderschoenen/regenlaarzen",
            "Snowboots": "https://www.shoesme.nl/kinderschoenen/snowboots",
            "Canvas sneakers": "https://www.shoesme.nl/kinderschoenen/canvas-sneakers",
        },
        "Peuter": {
            "Nieuw": "https://www.shoesme.nl/peuterschoenen/nieuw",
            "Vervolgschoentjes": "https://www.shoesme.nl/peuterschoenen/vervolgschoentjes",
            "Sandalen": "https://www.shoesme.nl/peuterschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/peuterschoenen/sneakers",
            "Meisjesschoenen": "https://www.shoesme.nl/peuterschoenen/meisjesschoenen",
            "Jongensschoenen": "https://www.shoesme.nl/peuterschoenen/jongensschoenen",
            "Laarzen": "https://www.shoesme.nl/peuterschoenen/laarzen",
        },
        "Baby": {
            "Nieuw": "https://www.shoesme.nl/babyschoenen/nieuw",
            "Slofjes": "https://www.shoesme.nl/babyschoenen/slofjes",
            "Eerste schoentjes": "https://www.shoesme.nl/babyschoenen/eerste-schoentjes",
            "Sandalen": "https://www.shoesme.nl/babyschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/babyschoenen/sneakers",
            "Vervolgschoentjes": "https://www.shoesme.nl/babyschoenen/vervolgschoentjes",
            "Laarzen & Boots": "https://www.shoesme.nl/babyschoenen/laarzen-boots",
        },
        "Meisjes": {
            "Nieuw": "https://www.shoesme.nl/meisjesschoenen/nieuw",
            "Zomerschoenen": "https://www.shoesme.nl/meisjesschoenen/zomerschoenen",
            "Babyschoenen": "https://www.shoesme.nl/meisjesschoenen/babyschoenen",
            "Sandalen": "https://www.shoesme.nl/meisjesschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/meisjesschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/meisjesschoenen/waterschoenen",
            "Bikerboots": "https://www.shoesme.nl/meisjesschoenen/bikerboots",
            "Chelsea boots": "https://www.shoesme.nl/meisjesschoenen/chelsea-boots",
            "Lage schoenen": "https://www.shoesme.nl/meisjesschoenen/lage-schoenen",
            "Hoge sneakers": "https://www.shoesme.nl/meisjesschoenen/hoge-sneakers",
            "Laarzen": "https://www.shoesme.nl/meisjesschoenen/laarzen",
            "Cowboylaarzen": "https://www.shoesme.nl/meisjesschoenen/cowboylaarzen",
            "Enkellaarsjes": "https://www.shoesme.nl/meisjesschoenen/enkellaarsjes",
            "Hoge schoenen & booties": "https://www.shoesme.nl/meisjesschoenen/hoge-schoenen-booties",
            "Winterschoenen": "https://www.shoesme.nl/meisjesschoenen/winterschoenen",
            "Regenlaarzen": "https://www.shoesme.nl/meisjesschoenen/regenlaarzen",
            "Snowboots": "https://www.shoesme.nl/meisjesschoenen/snowboots",
            "Pantoffels": "https://www.shoesme.nl/meisjesschoenen/pantoffels",
            "Canvas sneakers": "https://www.shoesme.nl/meisjesschoenen/canvas-sneakers",
            "Wintersneakers": "https://www.shoesme.nl/meisjesschoenen/wintersneakers",
        },
        "Jongens": {
            "Nieuw": "https://www.shoesme.nl/jongensschoenen/nieuw",
            "Zomerschoenen": "https://www.shoesme.nl/jongensschoenen/zomerschoenen",
            "Sandalen": "https://www.shoesme.nl/jongensschoenen/sandalen",
            "Babyschoenen": "https://www.shoesme.nl/jongensschoenen/babyschoenen",
            "Sneakers": "https://www.shoesme.nl/jongensschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/jongensschoenen/waterschoenen",
            "Boots": "https://www.shoesme.nl/jongensschoenen/boots",
            "Veterboots": "https://www.shoesme.nl/jongensschoenen/veterboots",
            "Chelsea boots": "https://www.shoesme.nl/jongensschoenen/chelsea-boots",
            "Lage schoenen": "https://www.shoesme.nl/jongensschoenen/lage-schoenen",
            "Hoge sneakers": "https://www.shoesme.nl/jongensschoenen/hoge-sneakers",
            "Pantoffels": "https://www.shoesme.nl/jongensschoenen/pantoffels",
            "Winterschoenen": "https://www.shoesme.nl/jongensschoenen/winterschoenen",
            "Regenlaarzen": "https://www.shoesme.nl/jongensschoenen/regenlaarzen",
            "Canvas sneakers": "https://www.shoesme.nl/jongensschoenen/canvas-sneakers",
        },
        "Go Banana's": {
            "Sneakers": "https://www.shoesme.nl/go-bananas/sneakers",
            "Boots": "https://www.shoesme.nl/go-bananas/boots",
            "Sandalen": "https://www.shoesme.nl/go-bananas/sandalen",
        },
        "Sale": {
            "Babyschoenen": "https://www.shoesme.nl/sale/babyschoenen",
            "Peuterschoenen": "https://www.shoesme.nl/sale/peuterschoenen",
            "Meisjesschoenen": "https://www.shoesme.nl/sale/meisjesschoenen",
            "Jongensschoenen": "https://www.shoesme.nl/sale/jongensschoenen",
            "Sneakers": "https://www.shoesme.nl/sale/sneakers",
            "Bikerboots": "https://www.shoesme.nl/sale/bikerboots",
            "Chelseaboots": "https://www.shoesme.nl/sale/chelseaboots",
            "Kinderlaarzen": "https://www.shoesme.nl/sale/kinderlaarzen",
            "Veterboots": "https://www.shoesme.nl/sale/veterboots",
            "Sandalen": "https://www.shoesme.nl/sale/sandalen",
        },
        "Accessoires": {
            "Rugzakken": "https://www.shoesme.nl/accessoires/rugzakken",
            "Onderhoudsartikelen": "https://www.shoesme.nl/accessoires/onderhoudsartikelen",
            "Schoenaccessoires": "https://www.shoesme.nl/accessoires/schoenaccessoires",
            "Sokken": "https://www.shoesme.nl/accessoires/sokken",
            "Drinkflessen": "https://www.shoesme.nl/accessoires/drinkflessen",
            "Kinderservies": "https://www.shoesme.nl/accessoires/kinderservies",
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
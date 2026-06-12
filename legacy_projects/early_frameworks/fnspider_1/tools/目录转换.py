import json

start_data = {
            "Kobieta": {
                "Ubrania": {
                    "SUMMER is popping": "https://www.housebrand.com/pl/pl/kobieta/ubrania/summer-popping",
                    "Nowości": "https://www.housebrand.com/pl/pl/kobieta/ubrania/nowosci",
                    "Bestsellers": "https://www.housebrand.com/pl/pl/kobieta/ubrania/bestsellers",
                    "Sukienki, kombinezony": "https://www.housebrand.com/pl/pl/kobieta/ubrania/sukienki-kombinezony",
                    "Koszulki, topy": "https://www.housebrand.com/pl/pl/kobieta/ubrania/koszulki-topy",
                    "Koszule": "https://www.housebrand.com/pl/pl/kobieta/ubrania/koszule",
                    "Szorty": "https://www.housebrand.com/pl/pl/kobieta/ubrania/szorty",
                    "Spódnice": "https://www.housebrand.com/pl/pl/kobieta/ubrania/spodnice",
                    "Bluzki": "https://www.housebrand.com/pl/pl/kobieta/ubrania/bluzki",
                    "Bluzy": "https://www.housebrand.com/pl/pl/kobieta/ubrania/bluzy",
                    "Swetry, kardigany": "https://www.housebrand.com/pl/pl/kobieta/ubrania/swetry-kardigany",
                    "Kurtki, płaszcze": "https://www.housebrand.com/pl/pl/kobieta/ubrania/kurtki-plaszcze",
                    "Jeansy": "https://www.housebrand.com/pl/pl/kobieta/ubrania/jeansy",
                    "Spodnie": "https://www.housebrand.com/pl/pl/kobieta/ubrania/spodnie",
                    "Stroje kąpielowe": "https://www.housebrand.com/pl/pl/kobieta/ubrania/stroje-kapielowe",
                    "House Print LAB": "https://www.housebrand.com/pl/pl/kobieta/ubrania/house-print-lab",
                },
                "Buty & dodatki": {
                    "Buty": "https://www.housebrand.com/pl/pl/kobieta/dodatki/buty",
                    "Torby, plecaki": "https://www.housebrand.com/pl/pl/kobieta/dodatki/torby-plecaki",
                    "Bielizna": "https://www.housebrand.com/pl/pl/kobieta/dodatki/bielizna",
                    "Skarpety": "https://www.housebrand.com/pl/pl/kobieta/dodatki/skarpety",
                    "Piżamy, homewear": "https://www.housebrand.com/pl/pl/kobieta/dodatki/pizamy-szlafroki",
                    "Czapki": "https://www.housebrand.com/pl/pl/kobieta/dodatki/czapki",
                    "Okulary": "https://www.housebrand.com/pl/pl/kobieta/dodatki/okulary",
                    "Paski, portfele": "https://www.housebrand.com/pl/pl/kobieta/dodatki/paski",
                    "Biżuteria": "https://www.housebrand.com/pl/pl/kobieta/dodatki/bizuteria",
                    "Breloki": "https://www.housebrand.com/pl/pl/kobieta/dodatki/breloki",
                    "Akcesoria do włosów": "https://www.housebrand.com/pl/pl/kobieta/dodatki/akcesoria-do-wlosow",
                    "Let's Custom! 🔧": "https://www.housebrand.com/pl/pl/kobieta/dodatki/lets-custom",
                    "Pozostałe akcesoria": "https://www.housebrand.com/pl/pl/kobieta/dodatki/akcesoria-lifestyle",
                    "Niższe ceny": "https://www.housebrand.com/pl/pl/kobieta/dodatki/discounted"
                },
                "Sprawdź to!": {
                    "Licencje": "https://www.housebrand.com/pl/pl/kobieta/sprawdz-to/licenses",
                    "POP STAR ENERGY": "https://www.housebrand.com/pl/pl/kobieta/sprawdz-to/seasonal-look-4",
                    "Na okazje": "https://www.housebrand.com/pl/pl/kobieta/sprawdz-to/seasonal-look-3",
                    "Leather": "https://www.housebrand.com/pl/pl/kobieta/sprawdz-to/seasonal-look",
                    "Influencers' Faves": "https://www.housebrand.com/pl/pl/kobieta/sprawdz-to/influ-faves"
                },
                "Klaudia Sadownik": {
                    "Sprawdź wszystko": "https://www.housebrand.com/pl/pl/kobieta/klaudia-sadownik/sprawdz-wszystko",
                    "Ubrania": "https://www.housebrand.com/pl/pl/kobieta/klaudia-sadownik/ubrania",
                    "Buty & dodatki": "https://www.housebrand.com/pl/pl/kobieta/klaudia-sadownik/dodatki"
                }
            },
            "Mężczyzna": {
                "Ubrania": {
                    "SUMMER is popping": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/summer-popping",
                    "Nowości": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/nowosci",
                    "Bestsellers": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/bestsellers",
                    "Koszulki": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/koszulki",
                    "Koszule": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/koszule",
                    "Szorty": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/szorty",
                    "Bluzy": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/bluzy",
                    "Swetry": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/swetry",
                    "Kurtki, płaszcze": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/kurtki-plaszcze",
                    "Jeansy": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/jeansy",
                    "Spodnie": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/spodnie",
                    "Szorty kąpielowe": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/szorty-kapielowe",
                    "House Print LAB": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/house-print-lab",
                    "Active Casual": "https://www.housebrand.com/pl/pl/mezczyzna/ubrania/seasonal-look-2",
                },
                "Buty & dodatki": {
                    "Buty": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/buty",
                    "Torby, plecaki": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/torby-plecaki",
                    "Bielizna, piżamy": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/bielizna",
                    "Skarpety": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/skarpety",
                    "Czapki": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/czapki",
                    "Okulary": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/okulary",
                    "Paski, portfele": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/paski",
                    "Biżuteria": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/bizuteria",
                    "Breloki": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/breloki",
                    "Pozostałe akcesoria": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/akcesoria-lifestyle",
                    "Niższe ceny": "https://www.housebrand.com/pl/pl/mezczyzna/dodatki/discounted"
                },
                "Sprawdź to!": {
                    "Licencje": "https://www.housebrand.com/pl/pl/mezczyzna/sprawdz-to/licencje",
                    "Strefa Kibica": "https://www.housebrand.com/pl/pl/mezczyzna/sprawdz-to/koszulki-pilkarskie-na-mundial",
                    "Na okazje": "https://www.housebrand.com/pl/pl/mezczyzna/sprawdz-to/seasonal-look-3",
                    "Influencers' Faves": "https://www.housebrand.com/pl/pl/mezczyzna/sprawdz-to/influ-faves"
                }
            },
            "Nowości": {
                "Nowości dla niej": "https://www.housebrand.com/pl/pl/newin/newin-woman",
                "Nowości dla niego": "https://www.housebrand.com/pl/pl/newin/newin-man"
            },
            "BASIC": {
                "Dla niej": {
                    "Sprawdź wszystko": "https://www.housebrand.com/pl/pl/basic/for-her/subclass-1",
                    "GÓRY 👕": "https://www.housebrand.com/pl/pl/basic/for-her/subclass-2",
                    "DOŁY👖": "https://www.housebrand.com/pl/pl/basic/for-her/subclass-3"
                },
                "Dla niego": {
                    "Sprawdź wszystko": "https://www.housebrand.com/pl/pl/basic/for-him/subclass-1",
                    "GÓRY 👕": "https://www.housebrand.com/pl/pl/basic/for-him/subclass-2",
                    "DOŁY 👖": "https://www.housebrand.com/pl/pl/basic/for-him/subclass-3"
                }
            },
            "Influencers' Faves": {
                "Dla niej": "https://www.housebrand.com/pl/pl/influ-faves/for-her",
                "Dla niego": "https://www.housebrand.com/pl/pl/influ-faves/for-him"
            }
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
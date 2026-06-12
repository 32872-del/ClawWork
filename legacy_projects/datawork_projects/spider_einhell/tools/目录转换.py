import json

start_data = {
            "Promocje": "https://einhell.pl/promocje/",
            "Sklep": "https://einhell.pl/sklep/",
            "Power X-Change": {
                "Ogrodowe urządzenia Power X-Change": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/",
                "Akumulatory i ładowarki": {
                    "Akumulatory": "https://einhell.pl/kategoria-produktu/akumulatory/",
                    "Ładowarki": "https://einhell.pl/kategoria-produktu/ladowarki/",
                    "Akcesoria do akumulatorów": "https://einhell.pl/kategoria-produktu/akcesoria-do-akumulatorow/",
                },
            },
            "Warsztat": {
                "Elektronarzędzia": {
                    "Seria Professional": "https://einhell.pl/kategoria-produktu/elektronarzedzia/pro/",
                    "Wiertarko-wkrętarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/wiertarko-wkretarki/",
                    "Wiertarki udarowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/wiertarki-udarowe/",
                    "Młoty udarowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/mloty-udarowe/",
                    "Szlifierki kątowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-katowe/",
                    "Multiszlifierki": "https://einhell.pl/kategoria-produktu/multiszlifierki/",
                    "Frezarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/frezarki/",
                    "Pilarki tarczowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pilarki-tarczowe/",
                    "Strugi ręczne": "https://einhell.pl/kategoria-produktu/strugi-reczne/",
                    "Szlifierki oscylacyjne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-oscylacyjne/",
                    "Szlifierki taśmowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-tasmowe/",
                    "Szlifierki do gipsu": "https://einhell.pl/kategoria-produktu/szlifierki-do-gipsu/",
                    "Mieszadła": "https://einhell.pl/kategoria-produktu/mieszadla/",
                    "Pistolety natryskowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pistolety-natryskowe/",
                    "Piły szablaste": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pily-szablaste/",
                    "Narzędzia wielofunkcyjne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/narzedzia-wielofunkcyjne/",
                },
                "Urządzenia stacjonarne": {
                    "Przecinarki do drewna": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/przecinarki-do-drewna/",
                    "Piły ukośne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/pily-ukosne-urzadzenia-stacjonarne/",
                    "Piły taśmowe": "https://einhell.pl/kategoria-produktu/pily-tasmowe/",
                    "Szlifierki stołowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/szlifierki-stolowe/",
                    "Wiertarki kolumnowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/wiertarki-kolumnowe/",
                    "Przecinarki do glazury": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/przecinarki-do-glazury/",
                    "Agregaty prądotwórcze": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/agregaty-pradotworcze/",
                    "Wciągarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/wciagarki/",
                },
                "Urządzenia czyszczące": {
                    "Odkurzacze": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-czyszczace/odkurzacze/",
                    "Szczotki": "https://einhell.pl/kategoria-produktu/akcesoria/szczotki/",
                    "Myjki i inne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-czyszczace/myjki-i-inne/",
                },
                "Narzędzia samochodowe": {
                    "Prostowniki i Jump Startery": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/prostowniki-i-jump-startery/",
                    "Kompresory": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/kompresory-narzedzia-samochodowe/",
                    "Polerki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/polerki/",
                },
            },
            "Ogród": {
                "Kosiarki": {
                    "Kosiarki akumulatorowe": "https://einhell.pl/kategoria-produktu/kosiarki-akumulatorowe/",
                    "Kosiarki spalinowe": "https://einhell.pl/kategoria-produktu/ogrod/kosiarki/kosiarki-spalinowe/",
                    "Kosiarki elektryczne": "https://einhell.pl/kategoria-produktu/kosiarki-elektryczne/",
                    "Roboty koszące": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/roboty-koszace/",
                },
                "Aeratory i wertykulatory": "https://einhell.pl/kategoria-produktu/ogrod/aeratory-i-wertykulatory/",
                "Glebogryzarki": "https://einhell.pl/kategoria-produktu/ogrod/glebogryzarki/",
                "Podkaszarki i kosy": "https://einhell.pl/kategoria-produktu/ogrod/podkaszarki-i-kosy/",
                "Pompy wodne": {
                    "Pompy uniwersalne do domu i ogrodu": "https://einhell.pl/kategoria-produktu/pompy-uniwersalne-do-domu-i-ogrodu/",
                    "Pompy zanurzeniowe do wody brudnej": "https://einhell.pl/kategoria-produktu/pompy-zanurzeniowe-do-wody-brudnej/",
                    "Pompy zanurzeniowe do wody czystej": "https://einhell.pl/kategoria-produktu/pompy-zanurzeniowe-do-wody-czystej/",
                    "Hydrofory": "https://einhell.pl/kategoria-produktu/ogrod/pompy-wodne/hydrofory/",
                },
                "Dmuchawy i odkurzacze": "https://einhell.pl/kategoria-produktu/ogrod/dmuchawy-i-odkurzacze/",
                "Nożyce do traw i żywopłotu": "https://einhell.pl/kategoria-produktu/ogrod/nozyce-do-traw-i-zywoplotu/",
                "Piły i nożyce do gałęzi": {
                    "Piły łańcuchowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pily-lancuchowe/",
                },
                "Urządzenia ogrodowe na wysięgniku": "https://einhell.pl/kategoria-produktu/ogrod/urzadzenia-ogrodowe-na-wysiegniku/",
                "Opryskiwacze": "https://einhell.pl/kategoria-produktu/ogrod/opryskiwacze/",
                "Pozostałe narzędzia ogrodowe": "https://einhell.pl/kategoria-produktu/pozostale-narzedzia-ogrodowe/",
                "Narzędzia ogrodowe PXC": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/",
            },
            "Akcesoria": {
                "Akcesoria do akumulatorów": "https://einhell.pl/kategoria-produktu/power-x-change/akumulatory-i-ladowarki/akcesoria-do-akumulatorow/",
                "Akcesoria do elektronarzędzi": "https://einhell.pl/kategoria-produktu/akcesoria-do-elektronarzedzi/",
                "Akcesoria do narzędzi wielofunkcyjnych": "https://einhell.pl/kategoria-produktu/akcesoria-do-narzedzi-wielofunkcyjnych/",
                "Akcesoria do wiertarko-wkrętarek": "https://einhell.pl/kategoria-produktu/akcesoria-do-wiertarko-wkretarek/",
                "Akcesoria do młotów udarowych": "https://einhell.pl/kategoria-produktu/akcesoria-do-mlotow-udarowych/",
                "Akcesoria do frezarek / strugów": "https://einhell.pl/kategoria-produktu/akcesoria-do-frezarek-strugow/",
                "Akcesoria do szlifierek/polerek": "https://einhell.pl/kategoria-produktu/akcesoria-do-szlifierek-polerek/",
                "Akcesoria do odkurzaczy": "https://einhell.pl/kategoria-produktu/akcesoria/akcesoria-do-odkurzaczy/",
                "Akcesoria do pistoletów malarskich": "https://einhell.pl/kategoria-produktu/akcesoria-do-pistoletow-malarskich/",
                "Akcesoria do pił": "https://einhell.pl/kategoria-produktu/akcesoria-do-pil/",
                "Akcesoria do podkaszarek": "https://einhell.pl/kategoria-produktu/akcesoria-do-podkaszarek/",
                "Zestawy akcesoriów": "https://einhell.pl/kategoria-produktu/akcesoria/zestawy-akcesoriow/",
                "Organizacja warsztatu": "https://einhell.pl/organizacja-watsztatu/",
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
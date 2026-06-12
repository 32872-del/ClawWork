import json

start_data = {
    "Babyaccessoires": {
        "Fopspenen": "https://www.etos.nl/babyaccessoires/fopspenen/"
    },
    "Babyvoeding": {
        "Flesvoeding": "https://www.etos.nl/babyvoeding/flesvoeding/"
    },
    "Beauty": {
        "Gezichtsverzorging": "https://www.etos.nl/s/etos-nl/beauty/gezichtsverzorging/",
        "Giftsets": "https://www.etos.nl/beauty/giftsets/",
        "Haarverzorging": "https://www.etos.nl/beauty/haarverzorging/",
        "Make-up": {
            "Gezichtsmake-up": "https://www.etos.nl/s/etos-nl/make-up/gezicht/",
            "Lipmake-up": "https://www.etos.nl/s/etos-nl/make-up/lip/",
            "Make-upaccessoires": "https://www.etos.nl/s/etos-nl/make-up/accessoires/",
            "Make-upreiniging": "https://www.etos.nl/s/etos-nl/make-up/reiniging/",
            "Nagels": "https://www.etos.nl/s/etos-nl/make-up/nagels/",
            "Oogmake-up": "https://www.etos.nl/s/etos-nl/make-up/oog/",
            "Wenkbrauwmake-up": "https://www.etos.nl/s/etos-nl/make-up/wenkbrauwen/"
        },
        "Parfum": {
            "Damesparfum": "https://www.etos.nl/s/etos-nl/parfum/dames/",
            "Herengeuren": "https://www.etos.nl/s/etos-nl/parfum/heren/"
        }
    },
    "Cadeau": {
        "Parfum": "https://www.etos.nl/cadeau/parfum/"
    },
    "Cadeaus": {
        "Gift sets": "https://www.etos.nl/s/etos-nl/beauty/giftsets/"
    },
    "Folder acties": {
        "Acties per categorie": "https://www.etos.nl/folder-acties/acties-per-categorie/",
        "Type aanbieding": "https://www.etos.nl/folder-acties/type-aanbieding/"
    },
    "Gezichtsverzorging": {
        "Gezichtsserum": "https://www.etos.nl/gezichtsverzorging/gezichtsserum/"
    },
    "Gezondheid": {
        "Bescherming Hygiene": {
            "Thermometers": "https://www.etos.nl/gezondheid/bescherming-hygiene/thermometers/"
        },
        "Optiek": "https://www.etos.nl/gezondheid/optiek/",
        "Seksualiteit": {
            "Seksspeeltjes": "https://www.etos.nl/s/etos-nl/seksualiteit/seksspeeltjes/"
        },
        "Speciale huidverzorging": "https://www.etos.nl/gezondheid/speciale-huidverzorging/",
        "Sport": {
            "Sportvoeding": "https://www.etos.nl/gezondheid/sport/sportvoeding/"
        },
        "Vitamines & supplementen": {
            "Mineralen": "https://www.etos.nl/s/etos-nl/vitamines-mineralen-en-supplementen/mineralen/",
            "Vitamines": "https://www.etos.nl/s/etos-nl/vitamines-mineralen-en-supplementen/vitamines/",
            "Voedingssupplementen": "https://www.etos.nl/s/etos-nl/vitamines-mineralen-en-supplementen/supplementen/"
        },
        "Vitamines Supplementen": {
            "Mineralen": "https://www.etos.nl/gezondheid/vitamines-supplementen/mineralen/magnesium/lucovitaal-magnesium/",
            "Vitamines": "https://www.etos.nl/gezondheid/vitamines-supplementen/vitamines/multivitamines/dagravit-multivitamines/",
            "Voedingssupplementen": "https://www.etos.nl/gezondheid/vitamines-supplementen/voedingssupplementen/weerstand-energie/lucovitaal-weerstand-energie-supplementen/"
        },
        "Voeding": {
            "Gewichtsbeheersing": "https://www.etos.nl/gezondheid/voeding/gewichtsbeheersing/"
        },
        "Voetongemakken": "https://www.etos.nl/gezondheid/voetongemakken/",
        "Wondverzorging": "https://www.etos.nl/s/etos-nl/wondverzorging/",
        "Zelfzorg": {
            "Allergie": "https://www.etos.nl/s/etos-nl/zelfzorg/allergie/",
            "Anti-insect": "https://www.etos.nl/s/etos-nl/op-reis/anti-insect/",
            "Darm": "https://www.etos.nl/s/etos-nl/zelfzorg/darm/",
            "Hoofdluis": "https://www.etos.nl/gezondheid/zelfzorg/hoofdluis/",
            "Luchtwegen": "https://www.etos.nl/s/etos-nl/zelfzorg/luchtwegen/",
            "Maag": "https://www.etos.nl/s/etos-nl/zelfzorg/maag/",
            "Mond, oog & oor": "https://www.etos.nl/gezondheid/zelfzorg/mond-oog-en-oor/",
            "Pijn": "https://www.etos.nl/s/etos-nl/zelfzorg/pijn/",
            "Pijnstillers": "https://www.etos.nl/s/etos-nl/gezondheid/zelfzorg/pijnstillers/",
            "Spieren & gewrichten": "https://www.etos.nl/s/etos-nl/zelfzorg/spieren-en-gewrichten/",
            "Stoppen met roken": "https://www.etos.nl/gezondheid/zelfzorg/stoppen-met-roken/",
            "Thermometers": "https://www.etos.nl/gezondheid/bescherming-hygiene/thermometers/",
            "Vrouw": "https://www.etos.nl/s/etos-nl/zelfzorg/vrouw/",
            "Zelftesten": "https://www.etos.nl/s/etos-nl/overige-hulpmiddelen/zelftesten/",
            "Zelfzorg kind": "https://www.etos.nl/s/etos-nl/zelfzorg/kind/"
        }
    },
    "Mondhygiene": {
        "Elektrische Tandenborstels": "https://www.etos.nl/mondhygiene/elektrische-tandenborstels/"
    },
    "Overige Hulpmiddelen": {
        "Meters": {
            "Thermometers": "https://www.etos.nl/overige-hulpmiddelen/meters/thermometers/"
        }
    },
    "Thuis & Op Reis": {
        "Huishouden": {
            "Wasmiddel": "https://www.etos.nl/s/etos-nl/huishouden/wasmiddel/"
        },
        "Kleding": "https://www.etos.nl/thuis-en-op-reis/kleding/",
        "Op reis": "https://www.etos.nl/thuis-en-op-reis/op-reis/",
        "Thuis & lifestyle": "https://www.etos.nl/thuis-en-op-reis/thuis-en-lifestyle/",
        "Voeding": "https://www.etos.nl/s/etos-nl/voeding/"
    },
    "Verschonen": {
        "Luiers": "https://www.etos.nl/verschonen/luiers/"
    },
    "Verzorging": {
        "Accessoires": "https://www.etos.nl/s/etos-nl/beauty-accessoires/",
        "Dermacare": {
            "Avène": "https://www.etos.nl/s/etos-nl/dermacare/avene/",
            "CeraVe": "https://www.etos.nl/s/etos-nl/dermacare/cerave/",
            "Drs Leenarts": "https://www.etos.nl/merken/drs-leenarts/",
            "Eucerin": "https://www.etos.nl/s/etos-nl/dermacare/eucerin/",
            "La Roche-Posay": "https://www.etos.nl/s/etos-nl/dermacare/la-roche-posay/",
            "Louis Widmer": "https://www.etos.nl/verzorging/dermacare/louis-widmer/",
            "Vichy": "https://www.etos.nl/s/etos-nl/dermacare/vichy/"
        },
        "Gezichtsverzorging": {
            "Dagcrème": "https://www.etos.nl/s/etos-nl/gezichtsverzorging/dagcreme/",
            "Gezichtsreiniging": "https://www.etos.nl/s/etos-nl/gezichtsreiniging/",
            "Gezichtsserum": "https://www.etos.nl/s/etos-nl/gezichtsverzorging/gezichtsserum/",
            "Lipverzorging": "https://www.etos.nl/make-up/lip/lipverzorging/"
        },
        "Haarverzorging": {
            "Accessoires": "https://www.etos.nl/s/etos-nl/beauty-accessoires/",
            "Haarstyling": "https://www.etos.nl/s/etos-nl/haarstyling/",
            "Haarverf": "https://www.etos.nl/s/etos-nl/haarstyling/haarverf/",
            "Shampoo": "https://www.etos.nl/s/etos-nl/haarverzorging/shampoo/"
        },
        "Heren verzorging": "https://www.etos.nl/s/etos-nl/verzorging/mannen/",
        "Lichaamsverzorging": {
            "Bad & douche": "https://www.etos.nl/s/etos-nl/lichaamsverzorging/bad-douche/",
            "Handverzorging": "https://www.etos.nl/s/etos-nl/huid-hand/handverzorging/",
            "Huidverzorging": "https://www.etos.nl/s/etos-nl/huid-hand/huidverzorging/",
            "Intieme verzorging": "https://www.etos.nl/s/etos-nl/intieme-hygiene/",
            "Scheren & ontharing": "https://www.etos.nl/s/etos-nl/lichaamsverzorging/scheren-ontharing/",
            "Voetverzorging": "https://www.etos.nl/verzorging/lichaamsverzorging/voetverzorging/",
            "Zonbescherming": "https://www.etos.nl/s/etos-nl/lichaamsverzorging/zonbescherming/"
        },
        "Mondhygiene": {
            "Elektrische Tandenborstels": "https://www.etos.nl/verzorging/mondhygiene/elektrische-tandenborstels/opzetborstels/"
        },
        "Mondhygiëne": {
            "Elektrische tandenborstels": "https://www.etos.nl/s/etos-nl/mondhygiene/elektrische-tandenborstels/",
            "Flossen": "https://www.etos.nl/s/etos-nl/mondhygiene/flossen/"
        }
    },
    "Zwanger Baby Kind": {
        "Eten Drinken": {
            "Flesvoeding": "https://www.etos.nl/zwanger-baby-kind/eten-drinken/flesvoeding/opvolgmelk/etos-opvolgmelk/"
        },
        "Verschonen": {
            "Billendoekjes": "https://www.etos.nl/zwanger-baby-kind/verschonen/billendoekjes/etos-billendoekjes/"
        }
    },
    "Zwanger, Baby & Kind": {
        "Baby & kind accessoires": {
            "Fopspenen": "https://www.etos.nl/s/etos-nl/babyaccessoires/fopspenen/"
        },
        "Babyverzorging": "https://www.etos.nl/dermacare/drs-leenarts/babyverzorging/",
        "Eten & drinken": {
            "Babyvoeding": "https://www.etos.nl/s/etos-nl/babyvoeding/",
            "Flesvoeding": "https://www.etos.nl/s/etos-nl/babyvoeding/flesvoeding/"
        },
        "Kraamtijd": "https://www.etos.nl/s/etos-nl/zwanger/kraamtijd/",
        "Verschonen": {
            "Billendoekjes": "https://www.etos.nl/s/etos-nl/verschonen/babydoekjes/",
            "Luiers": "https://www.etos.nl/s/etos-nl/verschonen/luiers/"
        },
        "Zwanger": "https://www.etos.nl/zwanger-baby-en-kind/zwanger/"
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
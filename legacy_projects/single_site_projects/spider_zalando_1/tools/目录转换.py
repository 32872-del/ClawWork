import json

start_data = {
            "Nieuw binnen": {
                "Categorie": {
                    "Nieuw": "https://be.pandora.net/nl/nieuw/",
                    "Bedels": "https://be.pandora.net/nl/nieuw/bedels/",
                    "Armbanden": "https://be.pandora.net/nl/nieuw/armbanden/",
                    "Ringen": "https://be.pandora.net/nl/nieuw/ringen/",
                    "Kettingen": "https://be.pandora.net/nl/nieuw/kettingen/",
                    "Oorbellen": "https://be.pandora.net/nl/nieuw/oorbellen/"
                },
                "Highlights": {
                    "Sieradendoosje Cadeau*": "https://be.pandora.net/nl/collecties/disney/?prefn1=featured&prefv1=Juwelen%20doosje%20cadeau",
                    "Klaar voor de lente": "https://be.pandora.net/nl/cadeaus/themas/klaar-voor-de-lente/",
                    "Pandora en Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "My Pandora Charm 2026": "https://be.pandora.net/nl/early-access-new-arrivals/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/",
                    "Pandora Minis": "https://be.pandora.net/nl/bedels/kleine-bedeltjes/"
                },
                "Gepersonaliseerde sieraden": {
                    "Armband + Bedel = 20%": "https://be.pandora.net/nl/armbanden/bedel-armbanden/style-your-story/",
                    "Ketting + Bedels = 20%": "https://be.pandora.net/nl/kettingen/gepersonaliseerde-kettingen-op-aanbiedingen/",
                    "Lettersieraden": "https://be.pandora.net/nl/bedels/categorie/alfabetische-bedels/",
                    "Sterrenbeelden": "https://be.pandora.net/nl/bedels/categorie/dierenriem-bedels/",
                    "Geboortestenen": "https://be.pandora.net/nl/bedels/categorie/geboortesteen/"
                }
            },
            "Ontdek collecties & meer": {
                "Collecties": {
                    "Pandora Moments": "https://be.pandora.net/nl/collecties/pandora-moments/#shop",
                    "Pandora en Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/#shop",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/#shop",
                    "Pandora ME": "https://be.pandora.net/nl/collecties/pandora-me/#shop",
                    "PANDORA ESSENCE": "https://be.pandora.net/nl/collecties/pandora-essence/#shop",
                    "Pandora Signature": "https://be.pandora.net/nl/collecties/pandora-signature/#shop",
                    "Marvel x Pandora": "https://be.pandora.net/nl/collecties/marvel/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/collecties/pandora-moments/lieve/#shop",
                    "Symbolen": "https://be.pandora.net/nl/collecties/pandora-moments/symbolen/#shop",
                    "Familie en Vrienden": "https://be.pandora.net/nl/collecties/pandora-moments/familie-vrienden/#shop",
                    "Reizen & Hobby's": "https://be.pandora.net/nl/collecties/pandora-moments/reizen-en-hobbys-charms/#shop",
                    "Gelegenheden & Vieringen": "https://be.pandora.net/nl/collecties/pandora-moments/gelegenheden-om-te-vieren/#shop",
                    "Dieren & Huisdieren": "https://be.pandora.net/nl/collecties/pandora-moments/dieren-huisdieren/#shop",
                    "Natuur & Hemels": "https://be.pandora.net/nl/collecties/pandora-moments/natuur-celestiaa/#shop"
                },
                "Gelegenheid": {
                    "Verjaardag": "https://be.pandora.net/nl/cadeaus/gelegenheden/verjaardag/#shop",
                    "Afstuderen": "https://be.pandora.net/nl/cadeaus/gelegenheden/afstuderen/#shop",
                    "Bruid & Bruidsmeisjes": "https://be.pandora.net/nl/cadeaus/gelegenheden/bruiloft-bruidsmeisjes/#shop",
                    "Nieuwe Mama & Baby": "https://be.pandora.net/nl/search/?cgid=gifts-mums-babies#shop",
                    "Jubileum": "https://be.pandora.net/nl/cadeaus/gelegenheden/jubileum/#shop"
                },
                "Prijs": {
                    "Onder €50": "https://be.pandora.net/nl/sieraden/?pmin=0.00&pmax=50.00#shop",
                    "Onder €100": "https://be.pandora.net/nl/sieraden/?pmin=50.00&pmax=100.00#shop",
                    "Onder €250": "https://be.pandora.net/nl/sieraden/?pmin=100.00&pmax=250.00#shop",
                    "Boven €250": "https://be.pandora.net/nl/sieraden/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/sieraden/vergulde/",
                    "Sterling zilver": "https://be.pandora.net/nl/sieraden/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/sieraden/rose-verguld",
                    "Parels": "https://be.pandora.net/nl/ontdek-collecties-meer/materiaal/parels/"
                }
            },
            "Bedels": {
                "Categorie": {
                    "Hangende bedels": "https://be.pandora.net/nl/bedels/hangende-bedels/",
                    "Clips": "https://be.pandora.net/nl/bedels/clips/",
                    "Pandora minis": "https://be.pandora.net/nl/bedels/kleine-bedeltjes/",
                    "Geboortesteen": "https://be.pandora.net/nl/bedels/categorie/geboortesteen/",
                    "Alfabetische bedels": "https://be.pandora.net/nl/bedels/categorie/alfabetische-bedels/",
                    "Dierenriem bedels": "https://be.pandora.net/nl/bedels/categorie/dierenriem-bedels/",
                    "Spacers": "https://be.pandora.net/nl/bedels/spacers/",
                    "Veiligheidsketting": "https://be.pandora.net/nl/bedels/veiligheidsketting/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/bedels/liefde",
                    "Symbolen": "https://be.pandora.net/nl/bedels/symbole",
                    "Familie en Vrienden": "https://be.pandora.net/nl/bedels/familie-en-vrienden",
                    "Reizen & Hobby's": "https://be.pandora.net/nl/bedels/reizen-en-hobbys",
                    "Gelegenheden & Vieringen": "https://be.pandora.net/nl/bedels/gelegenheden-om-te-vieren",
                    "Dieren & Huisdieren": "https://be.pandora.net/nl/bedels/dieren-en-huisdieren",
                    "Natuur & Hemels": "https://be.pandora.net/nl/bedels/natuur-en-sterrenhemel"
                },
                "Prijs": {
                    "Onder €50": "https://be.pandora.net/nl/bedels/?pmin=0.00&pmax=50.00#shop",
                    "Onder €100": "https://be.pandora.net/nl/bedels/?pmin=50.00&pmax=100.00#shop",
                    "Onder €250": "https://be.pandora.net/nl/bedels/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/bedels/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/bedels/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/bedels/rose-verguld"
                }
            },
            "Armbanden": {
                "Categorie": {
                    "Bedelarmbanden": "https://be.pandora.net/nl/armbanden/bedelarmbanden/",
                    "Parelarmbanden": "https://be.pandora.net/nl/armbanden/parel-armbanden/",
                    "Ketting armbanden": "https://be.pandora.net/nl/armbanden/ketting-armbanden/",
                    "Tennisarmbanden": "https://be.pandora.net/nl/armbanden/tennis-armbanden/",
                    "Bangles": "https://be.pandora.net/nl/armbanden/bangles/",
                    "Leren armbanden": "https://be.pandora.net/nl/armbanden/leren-armbanden/",
                    "Sliding armbanden": "https://be.pandora.net/nl/armbanden/sliding-armbanden/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/armbanden/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/armbanden/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/armbanden/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/armbanden/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/armbanden/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/armbanden/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/armbanden/rose-verguld"
                }
            },
            "Kettingen": {
                "Categorie": {
                    "Kettingen met Hanger": "https://be.pandora.net/nl/kettingen/kettingen-met-hanger/",
                    "Parelkettingen": "https://be.pandora.net/nl/kettingen/parel-kettingen/",
                    "Kettingen met bedels": "https://be.pandora.net/nl/kettingen/bedelkettingen/",
                    "Halskettingen": "https://be.pandora.net/nl/kettingen/halskettingen/",
                    "Hangers voor Kettingen": "https://be.pandora.net/nl/kettingen/hangers-voor-kettingen/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/kettingen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/kettingen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/kettingen/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/kettingen/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/kettingen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/kettingen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/kettingen/rose-verguld"
                }
            },
            "Ringen": {
                "Categorie": {
                    "Verlovingsringen": "https://be.pandora.net/nl/ringen/verlovingsringen/",
                    "Stapelringen": "https://be.pandora.net/nl/ringen/stapelringen/",
                    "Statement ringen": "https://be.pandora.net/nl/ringen/statement-ringen/",
                    "Parelringen": "https://be.pandora.net/nl/ringen/parel-ringen/"
                },
                "Price": {
                    "Under €50": "https://be.pandora.net/nl/ringen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/ringen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/ringen/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/ringen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/ringen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/ringen/rose-verguld"
                }
            },
            "Oorbellen": {
                "Categorie": {
                    "Oorknopjes": "https://be.pandora.net/nl/oorbellen/oorknopjes/",
                    "Oorringen": "https://be.pandora.net/nl/oorbellen/oorringen/",
                    "Pareloorbellen": "https://be.pandora.net/nl/oorbellen/parel-oorbellen/",
                    "Oorhangers": "https://be.pandora.net/nl/oorbellen/oorhangers/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/oorbellen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/oorbellen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/oorbellen/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/oorbellen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/oorbellen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/oorbellen/rose-verguld"
                }
            },
            "Cadeaus": {
                "Categorie": {
                    "Guide: Speciale Cadeau-Ideeen Vinden": "https://be.pandora.net/nl/cadeaus/",
                    "Armband + Bedels = 20%": "https://be.pandora.net/nl/armbanden/bedel-armbanden/style-your-story/",
                    "Ketting + Bedels = 20%": "https://be.pandora.net/nl/kettingen/gepersonaliseerde-kettingen-op-aanbiedingen/",
                    "Cadeausets": "https://be.pandora.net/nl/cadeaus/cadeau-ideeen/cadeausets/",
                    "Symbolische juwelen": "https://be.pandora.net/nl/cadeaus/categorie/symbolische-juwelen/",
                    "Verstelbare sieraden": "https://be.pandora.net/nl/cadeaus/sieraden-zonder-vaste-maat/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/collecties/pandora-moments/lieve/",
                    "Harten Sieraden": "https://be.pandora.net/nl/sieraden/harten-sieraden/",
                    "Klaar voor de lente": "https://be.pandora.net/nl/cadeaus/themas/klaar-voor-de-lente/",
                    "Bloemen Sieraden": "https://be.pandora.net/nl/cadeaus/themas/bloemen-sieraden/",
                    "Glitterende juwelen": "https://be.pandora.net/nl/cadeaus/themas/glitterende-juwelen/",
                    "Familie en vrienden": "https://be.pandora.net/nl/collecties/pandora-moments/familie-vrienden/",
                    "Symbolen": "https://be.pandora.net/nl/collecties/pandora-moments/symbolen/",
                    "Natuur en celestiaal": "https://be.pandora.net/nl/collecties/pandora-moments/natuur-celestiaa/",
                    "Dieren en huisdieren": "https://be.pandora.net/nl/collecties/pandora-moments/dieren-huisdieren/",
                    "Reizen en hobbys": "https://be.pandora.net/nl/collecties/pandora-moments/reizen-en-hobbys-charms/"
                },
                "Gelegenheden": {
                    "Moederdag": "https://be.pandora.net/nl/cadeaus/gelegenheden/moederdag/",
                    "Bruiloft & Bruid": "https://be.pandora.net/nl/cadeaus/gelegenheden/bruiloft-bruidsmeisjes/",
                    "Afstuderen": "https://be.pandora.net/nl/cadeaus/gelegenheden/afstuderen/",
                    "Verjaardag": "https://be.pandora.net/nl/cadeaus/gelegenheden/verjaardag/",
                    "Baby & Doop": "https://be.pandora.net/nl/cadeaus/gelegenheden/baby-doop/",
                    "Zomaar": "https://be.pandora.net/nl/gifts/occasions/just-because/",
                    "Vormsel": "https://be.pandora.net/nl/cadeaus/gelegenheden/vormsel/"
                },
                "Voor wie?": {
                    "Cadeaus voor je Geliefde": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-je-geliefde/",
                    "Cadeaus voor Moeders": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-moeder/",
                    "Cadeaus voor Oma": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-oma/",
                    "Cadeaus voor Vriendinnen": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-vriendinnen/",
                    "Cadeaus voor Dochters": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-dochters/",
                    "Cadeaus voor Zussen": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-zussen/",
                    "Cadeaus voor Hem": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-hem/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/sieraden/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/sieraden/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/sieraden/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/sieraden/?pmin=250.00&pmax=5,000.00#shop"
                }
            },
            "Collecties": {
                "Categorie": {
                    "Pandora Moments": "https://be.pandora.net/nl/collecties/pandora-moments/",
                    "Pandora and Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/",
                    "PANDORA MINIS": "https://be.pandora.net/nl/collecties/pandora-minis/",
                    "Pandora ME": "https://be.pandora.net/nl/collecties/pandora-me/",
                    "Marvel x Pandora": "https://be.pandora.net/nl/collecties/marvel/",
                    "PANDORA ESSENCE": "https://be.pandora.net/nl/collecties/pandora-essence/",
                    "Pandora Talisman": "https://be.pandora.net/nl/collecties/pandora-talisman/",
                    "Pandora Signature": "https://be.pandora.net/nl/collecties/pandora-signature/"
                }
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
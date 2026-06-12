import json

start_data = {
            'Produkte': {
                'Waschen & Trocknen': {
                    'Waschmaschinen': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waschmaschinen',
                    'Wäschetrockner': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waeschetrockner',
                    'Waschmaschine mit Trockner': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waschtrockner',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/zubehoer-trockner',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/pflege-reinigung',
                },
                'Geschirrspüler': {
                    'Einbaugeschirrspüler': 'https://www.bosch-home.com/de/de/category/geschirrspueler/einbaugeschirrspueler',
                    'Freistehende Geschirrspüler': 'https://www.bosch-home.com/de/de/category/geschirrspueler/geschirrspueler-freistehend',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/geschirrspueler/zubehoer-geschirrspueler',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/geschirrspueler/pflege-reinigung',
                },
                'Kühlen & Gefrieren': {
                    'Kühl-Gefrier-Kombinationen': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/kuehl-gefrier-kombinationen',
                    'Kühlschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/kuehlschraenke',
                    'Side-by-Side Kühl-Gefrier-Kombinationen': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/side-by-side-kuehlschraenke',
                    'French Door': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/french-door',
                    'Gefrierschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/gefrierschraenke',
                    'Weinkühlschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/weinkuehlschraenke',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/zubehoer-kuehlschraenke-gefrierschraenke',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/pflege-reinigung',
                },
                'Kochen & Backen': {
                    'Herde und Backöfen': 'https://www.bosch-home.com/de/de/category/kochen-backen/herde-backoefen',
                    'Kochfelder': 'https://www.bosch-home.com/de/de/category/kochen-backen/kochfelder',
                    'Gaskochfelder': 'https://www.bosch-home.com/de/de/category/kochen-backen/gaskochfelder',
                    'Freistehende Herde': 'https://www.bosch-home.com/de/de/category/kochen-backen/freistehende-herde',
                    'Dampfbacköfen und Dampfgarer': 'https://www.bosch-home.com/de/de/category/kochen-backen/dampfbackoefen-dampfgarer',
                    'Mikrowellen': 'https://www.bosch-home.com/de/de/category/kochen-backen/mikrowellen',
                    'Dunstabzugshauben': 'https://www.bosch-home.com/de/de/category/kochen-backen/dunstabzugshauben',
                    'Wärmeschubladen': 'https://www.bosch-home.com/de/de/category/kochen-backen/waermeschubladen',
                    'Kontaktgrills': 'https://www.bosch-home.com/de/de/category/kochen-backen/kontaktgrill',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kochen-backen/kochzubehoer-backzubehoer',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kochen-backen/pflege-reinigung',
                },
                'Cookit Küchenmaschine mit Kochfunktion': {
                    'Cookit Küchenmaschine mit Kochfunktion': 'https://www.bosch-home.com/de/de/category/kuechenmaschinemitkochfunktion',
                    'Zubehör für Cookit': 'https://www.bosch-home.com/de/de/category/kuechenmaschinemitkochfunktion/cookit-zubehoer',
                },
                'Küchenmaschinen': {
                    'Küchenmaschinen Serie': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/mum-kuechenmaschinen',
                    'Kompakt-Küchenmaschine': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/kompakt-kuechenmaschinen',
                    'Zubehör für Küchenmaschinen': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/zubehoer-kuechenmaschinen',
                },
                'Kleine Küchengeräte': {
                    'Heißluftfritteusen': 'https://www.bosch-home.com/de/de/category/kuechengeraete/air-fryer',
                    'Stabmixer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/stabmixer',
                    'Handrührer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/handruehrgeraete',
                    'Standmixer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/standmixer',
                    'Entsafter & Saftpressen': 'https://www.bosch-home.com/de/de/category/kuechengeraete/entsafter-saftpressen',
                    'Universalzerkleinerer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/universalzerkleinerer',
                    'Toaster': 'https://www.bosch-home.com/de/de/category/kuechengeraete/toaster',
                    'Wasserkocher': 'https://www.bosch-home.com/de/de/category/kuechengeraete/wasserkocher',
                    'Fleischwölfe': 'https://www.bosch-home.com/de/de/category/kuechengeraete/fleischwoelfe',
                    'Kontaktgrills': 'https://www.bosch-home.com/de/de/category/kuechengeraete/kontaktgrill',
                },
                'Kaffeemaschinen': {
                    'Kaffeevollautomaten': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/kaffeevollautomaten',
                    'Einbau-Kaffeevollautomaten': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/einbau-kaffeevollautomaten',
                    'Filterkaffeemaschinen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/filterkaffeemaschinen',
                    'Kaffeemühlen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/kaffeemuehlen',
                    'TASSIMO Kapselmaschinen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/tassimo-kapselmaschinen',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/zubehoer-kaffeemaschinen',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/entkalkung-reinigung',
                },
                'Staubsauger': {
                    'Akku-Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/kabellose-handstaubsauger',
                    'Saugroboter': 'https://www.bosch-home.com/de/de/category/staubsauger/saugroboter',
                    'Beutellose Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/beutellose-staubsauger',
                    'Staubsauger mit Beutel': 'https://www.bosch-home.com/de/de/category/staubsauger/staubsauger-mit-beutel',
                    'Handstaubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/akkusauger',
                    'Zubehör für Akku-Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-akkustaubsauger',
                    'Zubehör für Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-staubsauger',
                    'Built in cleaning robot': 'https://www.bosch-home.com/de/de/category/staubsauger/built-in-cleaning-robot',
                    'Zubehör für Saugroboter': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-staubsauger/bosch-saugroboter-zubehoer-shop',
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
import json

start_data = {
            "MULHER": {
                "NOVIDADES": "https://www.lanidor.com/pt/mulher/coleccao/novidades/lst/d/14/",
                "YOU & ME": "https://www.lanidor.com/pt/mulher/coleccao/you-me/lst/d/161/",
                "VESTIDOS": "https://www.lanidor.com/pt/mulher/coleccao/vestidos/lst/c/10/",
                "CALÇAS": "https://www.lanidor.com/pt/mulher/coleccao/calcas/lst/c/4/",
                "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/mulher/coleccao/camisas-e-tunicas/lst/c/49/",
                "MALHAS": "https://www.lanidor.com/pt/mulher/coleccao/malhas/lst/c/11/",
                "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/mulher/coleccao/t-shirts-e-tops/lst/c/158/",
                "CASACOS": "https://www.lanidor.com/pt/mulher/coleccao/casacos/lst/c/1/",
                "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/mulher/coleccao/saias-e-calcoes/lst/c/154/",
                "KAFTANS E PONCHOS": "https://www.lanidor.com/pt/mulher/coleccao/kaftans-e-ponchos-/lst/c/149/",
                "PIJAMAS": "https://www.lanidor.com/pt/mulher/coleccao/pijamas/lst/c/161/",
                "CALÇADO": "https://www.lanidor.com/pt/mulher/coleccao/calcado/lst/c/178/",
                "LENÇOS E ÉCHARPES": "https://www.lanidor.com/pt/mulher/coleccao/lencos-e-echarpes/lst/c/150/",
                "BIJUTERIA": "https://www.lanidor.com/pt/mulher/coleccao/bijuteria/lst/c/17/",
                "FATOS DE BANHO": "https://www.lanidor.com/pt/mulher/coleccao/fatos-banho/lst/c/83/",
                "MALAS": "https://www.lanidor.com/pt/mulher/coleccao/malas/lst/c/186/",
                "ACESSÓRIOS": "https://www.lanidor.com/pt/mulher/coleccao/acessorios/lst/c/26/",
                "PAREOS": "https://www.lanidor.com/pt/mulher/coleccao/pareos/lst/c/189/",
                "BLACK LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/mulher/coleccao/black-label-made-portugal/lst/d/1/",
                # Friendly Brands - 二级分类, 含3个三级分类
                "FRIENDLY BRANDS": {
                    "PABLO FUSTER": "https://www.lanidor.com/pt/mulher/coleccao/pablo-fuster/lst/?pc=1&brands=14",
                    "REVLON": "https://www.lanidor.com/pt/mulher/coleccao/revlon/lst/?pc=1&brands=15",
                    "THROTTLEMAN": "https://www.lanidor.com/pt/mulher/coleccao/throttleman/lst/?pc=1&brands=19",
                },
            },
            "CRIANÇA": {
                "MENINA": {
                    "NOVIDADES": "https://www.lanidor.com/pt/crianca-menina/coleccao/novidades/lst/d/14/",
                    "ROYAL LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/crianca-menina/coleccao/royal-label-made-portugal/lst/d/2/",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menina/coleccao/baby-collection/lst/c/91/",
                    "VESTIDOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/vestidos/lst/c/10/",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/crianca-menina/coleccao/t-shirts-e-tops/lst/c/158/",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/calcas/lst/c/4/",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/crianca-menina/coleccao/saias-e-calcoes/lst/c/154/",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menina/coleccao/sweats/lst/c/43/",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/camisas-e-tunicas/lst/c/49/",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menina/coleccao/praia/lst/c/139/",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/casacos/lst/c/1/",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/malhas/lst/c/11/",
                    "MACACÕES": "https://www.lanidor.com/pt/crianca-menina/coleccao/macacoes/lst/c/157/",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menina/coleccao/bijuteria/lst/c/17/",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/acessorios/lst/c/26/",
                },
                "MENINO": {
                    "NOVIDADES": "https://www.lanidor.com/pt/crianca-menino/coleccao/novidades/lst/d/14/",
                    "ROYAL LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/crianca-menino/coleccao/royal-label-made-portugal/lst/d/2/",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menino/coleccao/baby-collection/lst/c/91/",
                    "T-SHIRTS": "https://www.lanidor.com/pt/crianca-menino/coleccao/t-shirts/lst/c/23/",
                    "CALÇÕES": "https://www.lanidor.com/pt/crianca-menino/coleccao/calcoes/lst/c/5/",
                    "POLOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/polos/lst/c/41/",
                    "CAMISAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/camisas/lst/c/22/",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/calcas/lst/c/4/",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/casacos/lst/c/1/",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menino/coleccao/praia/lst/c/139/",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menino/coleccao/sweats/lst/c/43/",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/malhas/lst/c/11/",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menino/coleccao/bijuteria/lst/c/17/",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/acessorios/lst/c/26/",
                },
            },
            "HOMEM": {
                "POLOS": "https://www.lanidor.com/pt/homem/coleccao/polos/lst/c/41/",
                "CAMISAS": "https://www.lanidor.com/pt/homem/coleccao/camisas/lst/c/22/",
                "CALÇAS": "https://www.lanidor.com/pt/homem/coleccao/calcas/lst/c/4/",
                "BOXER SHORTS": "https://www.lanidor.com/pt/homem/coleccao/boxer-shorts/lst/c/148/",
                "T-SHIRTS": "https://www.lanidor.com/pt/homem/coleccao/t-shirts/lst/c/23/",
                "CALÇÕES": "https://www.lanidor.com/pt/homem/coleccao/calcoes/lst/c/5/",
                "CALÇÕES DE BANHO": "https://www.lanidor.com/pt/homem/coleccao/calcoes-banho/lst/c/84/",
                "CASACOS": "https://www.lanidor.com/pt/homem/coleccao/casacos/lst/c/1/",
                "SWEATS": "https://www.lanidor.com/pt/homem/coleccao/sweats/lst/c/43/",
                "MALHAS": "https://www.lanidor.com/pt/homem/coleccao/malhas/lst/c/11/",
                "CALÇADO": "https://www.lanidor.com/pt/homem/coleccao/calcado/lst/c/13/",
                "ACESSÓRIOS": "https://www.lanidor.com/pt/homem/coleccao/acessorios/lst/c/26/",
            },
            "OUTLET": {
                "MULHER": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/mulher/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "VESTIDOS": "https://www.lanidor.com/pt/mulher/outlet/vestidos/lst/c/10/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/mulher/outlet/malhas/lst/c/11/?estacao=ss",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/mulher/outlet/t-shirts-e-tops/lst/c/158/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/mulher/outlet/calcas/lst/c/4/?estacao=ss",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/mulher/outlet/camisas-e-tunicas/lst/c/49/?estacao=ss",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/mulher/outlet/saias-e-calcoes/lst/c/154/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/mulher/outlet/casacos/lst/c/1/?estacao=ss",
                    "KAFTANS E PONCHOS": "https://www.lanidor.com/pt/mulher/outlet/kaftans-e-ponchos-/lst/c/149/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/mulher/outlet/sweats/lst/c/43/?estacao=ss",
                    "SAIAS": "https://www.lanidor.com/pt/mulher/outlet/saias/lst/c/8/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/mulher/outlet/praia/lst/c/139/?estacao=ss",
                    "CALÇADO": "https://www.lanidor.com/pt/mulher/outlet/calcado/lst/c/13/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/mulher/outlet/bijuteria/lst/c/17/?estacao=ss",
                    "FATOS DE BANHO": "https://www.lanidor.com/pt/mulher/outlet/fatos-banho/lst/c/83/?estacao=ss",
                    "LENÇOS E ÉCHARPES": "https://www.lanidor.com/pt/mulher/outlet/lencos-e-echarpes/lst/c/150/?estacao=ss",
                    "MALAS": "https://www.lanidor.com/pt/mulher/outlet/malas/lst/c/183/?estacao=ss",
                    "ACESSÓRIOS DE PRAIA": "https://www.lanidor.com/pt/mulher/outlet/acessorios-praia/lst/c/20/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/mulher/outlet/acessorios/lst/c/26/?estacao=ss",
                    "PAREOS": "https://www.lanidor.com/pt/mulher/outlet/pareos/lst/c/189/?estacao=ss",
                    "CASACOS MALHAS VESTIDOS": "https://www.lanidor.com/pt/mulher/outlet/casacos-malhas-vestidos/lst/c/11,10,1/?estacao=ss",
                    "MALHAS SAIAS CALÇÕES VESTIDOS": "https://www.lanidor.com/pt/mulher/coleccao/malhas-saias-e-calcoes-vestidos/lst/c/10,11,154/?brands=3",
                },
                "MENINA": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/crianca-menina/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menina/outlet/baby-collection/lst/c/91/?estacao=ss",
                    "VESTIDOS E MACACÕES": "https://www.lanidor.com/pt/crianca-menina/outlet/vestidos-e-macacoes/lst/c/180/?estacao=ss",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/crianca-menina/outlet/t-shirts-e-tops/lst/c/158/?estacao=ss",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/crianca-menina/outlet/saias-e-calcoes/lst/c/154/?estacao=ss",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/crianca-menina/outlet/camisas-e-tunicas/lst/c/49/?estacao=ss",
                    "COLECÇÃO BABY": "https://www.lanidor.com/pt/crianca-menina/outlet/coleccao-baby/lst/c/61/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menina/outlet/praia/lst/c/139/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menina/outlet/calcas/lst/c/4/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menina/outlet/casacos/lst/c/1/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menina/outlet/sweats/lst/c/43/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menina/outlet/malhas/lst/c/11/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menina/outlet/acessorios/lst/c/26/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menina/outlet/bijuteria/lst/c/17/?estacao=ss",
                },
                "MENINO": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/crianca-menino/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menino/outlet/baby-collection/lst/c/91/?estacao=ss",
                    "T-SHIRTS": "https://www.lanidor.com/pt/crianca-menino/outlet/t-shirts/lst/c/23/?estacao=ss",
                    "CALÇÕES": "https://www.lanidor.com/pt/crianca-menino/outlet/calcoes/lst/c/5/?estacao=ss",
                    "CAMISAS": "https://www.lanidor.com/pt/crianca-menino/outlet/camisas/lst/c/22/?estacao=ss",
                    "POLOS": "https://www.lanidor.com/pt/crianca-menino/outlet/polos/lst/c/41/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menino/outlet/calcas/lst/c/4/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menino/outlet/praia/lst/c/139/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menino/outlet/casacos/lst/c/1/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menino/outlet/sweats/lst/c/43/?estacao=ss",
                    "COLECÇÃO BABY": "https://www.lanidor.com/pt/crianca-menino/outlet/coleccao-baby/lst/c/61/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menino/outlet/malhas/lst/c/11/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menino/outlet/acessorios/lst/c/26/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menino/outlet/bijuteria/lst/c/17/?estacao=ss",
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
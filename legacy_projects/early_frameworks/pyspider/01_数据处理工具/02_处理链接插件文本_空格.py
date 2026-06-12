import json

# 原始数据
raw_data = """Bags	https://www.burton.com/pl/en/c/bags-luggage-bags
Backpacks and Rucksacks	https://www.burton.com/pl/en/c/backpacks-shoulder-bags
Kids Backpacks	https://www.burton.com/pl/en/c/youth-backpacks
Accessory Bags & Pouches	https://www.burton.com/pl/en/c/accessory-bags-pouches
Luggage	https://www.burton.com/pl/en/c/bags-luggage-luggage
Snowboard Travel Bags	https://www.burton.com/pl/en/c/snowboard-travel-bags
Checked Luggage	https://www.burton.com/pl/en/c/checked-luggage
Carry-On Luggage	https://www.burton.com/pl/en/c/carry-on-luggage
Duffel Bags	https://www.burton.com/pl/en/c/duffel-bags
Shop All Luggage	https://www.burton.com/pl/en/c/luggage-travel-bags
Accessories	https://www.burton.com/pl/en/c/accessories
Gloves & Mittens	https://www.burton.com/pl/en/c/gloves
Hats & Beanies	https://www.burton.com/pl/en/c/headwear-beanies
Neck Warmers & Face Masks	https://www.burton.com/pl/en/c/face-masks-neck-warmers
Socks	https://www.burton.com/pl/en/c/socks
Sunglasses	https://www.burton.com/pl/en/c/sunglasses
Collectibles	https://www.burton.com/pl/en/c/collectibles
Featured	https://www.burton.com/pl/en/c/bags-collections
Winter's Favorites	https://www.burton.com/pl/en/c/bags-top-sellers
Multipath Bags Collection	https://www.burton.com/pl/en/c/multipath-collection
Snow Backpacks	https://www.burton.com/pl/en/c/snow-backpacks
Protection	https://www.burton.com/pl/en/c/accessories-protection
Anon Goggles & Lenses	https://www.burton.com/pl/en/c/accessories-anon-goggles-lenses-rd
Anon Helmets	https://www.burton.com/pl/en/c/accessories-anon-helmets-rd
Protective Gear	https://www.burton.com/pl/en/c/accessories-protective-gear-rd
Burton [ak]® Dispatcher 35L Backpack	https://www.burton.com/pl/en/p/burton-ak-dispatcher-35l-backpack/W26-227981.html
Men	https://www.burton.com/pl/en/c/mens
Snowboarding	https://www.burton.com/pl/en/c/mens-snowboarding

"""


key_value_dict = {}
key_count = {}

# 按行处理数据
lines = raw_data.strip().split('\n')
for line in lines:
    parts = line.split('\t', 1)
    original_key = parts[0].strip() if len(parts) > 0 else ""
    value = parts[1].strip() if len(parts) > 1 else ""

    if value:
        if original_key in key_count:
            key_count[original_key] += 1
            new_key = f"{original_key} ({key_count[original_key]})"
        else:
            key_count[original_key] = 1
            new_key = original_key
        key_value_dict[new_key] = value
json_result = json.dumps(key_value_dict, indent=4, ensure_ascii=False)

print(json_result)
with open("axelarigato_key_value.json", "w", encoding="utf-8") as f:
    f.write(json_result)
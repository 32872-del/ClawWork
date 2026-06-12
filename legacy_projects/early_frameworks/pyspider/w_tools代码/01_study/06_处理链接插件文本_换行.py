import json
from collections import defaultdict

# 原始数据（名称和URL各占一行，交替出现）
raw_data = """
Sukienki z kieszeniami 22
https://www.riskmadeinwarsaw.com/collections/sukienki-z-kieszeniami
Sukienki kopertowe 9
https://www.riskmadeinwarsaw.com/collections/sukienki-kopertowe
Sukienki we wzory 17
https://www.riskmadeinwarsaw.com/collections/sukienki-we-wzory
Sukienki z długim rękawem 23
https://www.riskmadeinwarsaw.com/collections/sukienki-z-dlugim-rekawem
Sukienki czarne 12
https://www.riskmadeinwarsaw.com/collections/czarne-sukienki
Sukienki na wiosnę 30
https://www.riskmadeinwarsaw.com/collections/sukienki-na-wiosne
Zobacz wszystko 47
https://www.riskmadeinwarsaw.com/collections/sukienki
Spódnice 14
https://www.riskmadeinwarsaw.com/collections/spodnice
Kombinezony 4
https://www.riskmadeinwarsaw.com/collections/kombinezony
Spodnie 28
https://www.riskmadeinwarsaw.com/collections/spodnie
Bluzy 13
https://www.riskmadeinwarsaw.com/collections/bluzy
Koszule 4
https://www.riskmadeinwarsaw.com/collections/koszule
Marynarki 8
https://www.riskmadeinwarsaw.com/collections/marynarki
Kardigany i swetry 1
https://www.riskmadeinwarsaw.com/collections/kardigany-i-swetry
Bluzki i tiszerty 28
https://www.riskmadeinwarsaw.com/collections/bluzki-i-tiszerty
Kurtki 2
https://www.riskmadeinwarsaw.com/collections/kurtki
Akcesoria 4
https://www.riskmadeinwarsaw.com/collections/akcesoria
"""

# 按行分割，过滤空行
lines = raw_data.strip().split('\n')
filtered_lines = [line.strip() for line in lines if line.strip()]

# 初始化字典来跟踪每个键的出现次数
key_count = defaultdict(int)
# 初始化最终的键值对字典
key_value_dict = {}

# 按「两行一组」提取（第1行=键，第2行=值）
for i in range(0, len(filtered_lines), 2):
    if i + 1 < len(filtered_lines):  # 确保有对应的URL行
        original_key = filtered_lines[i]
        value = filtered_lines[i + 1]

        if original_key and value:
            # 增加该键的出现计数
            key_count[original_key] += 1

            # 根据出现次数生成带序号的新键
            if key_count[original_key] == 1:
                # 第一次出现，保持原键名
                new_key = original_key
            else:
                # 后续出现，添加序号
                new_key = f"{original_key}({key_count[original_key]})"

            # 添加到字典
            key_value_dict[new_key] = value

# 转换为格式化的JSON字符串
json_result = json.dumps(key_value_dict, indent=4, ensure_ascii=False)

# 打印结果
print(json_result)

# 保存到JSON文件
with open("hering_key_value.json", "w", encoding="utf-8") as f:
    f.write(json_result)

# 可选：打印统计信息
print(f"\n处理统计:")
print(f"总共处理了 {len(key_value_dict)} 个键值对")
print(f"重复键的处理:")
for key, count in key_count.items():
    if count > 1:
        print(f"  '{key}' 出现了 {count} 次")
import json
from collections import defaultdict

# 原始数据（名称和URL各占一行，交替出现）
raw_data = """Buty sezonowe
https://www.nagaba.pl/kategoria/buty-sezonowe-damskie
Buty letnie
https://www.nagaba.pl/kategoria/buty-letnie-damskie
Buty jesienne
https://www.nagaba.pl/kategoria/buty-jesienne-damskie
Buty zimowe
https://www.nagaba.pl/kategoria/buty-zimowe-damskie
Buty wiosenne
https://www.nagaba.pl/kategoria/buty-wiosenne-damskie
Trzewiki
https://www.nagaba.pl/kategoria/trzewiki-damskie
Skórzane
https://www.nagaba.pl/kategoria/trzewiki-damskie-skorzane
Zimowe
https://www.nagaba.pl/kategoria/trzewiki-damskie-zimowe
Zamszowe
https://www.nagaba.pl/kategoria/trzewiki-damskie-zamszowe
Brązowe
https://www.nagaba.pl/kategoria/trzewiki-damskie-brazowe
Trekkingi
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie
Turystyczne
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-turystyczne
Niskie
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-niskie
Wysokie
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-wysokie
Skóra naturalna
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-skora-naturalna
Czarne
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-czarne
Letnie
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-letnie
Zimowe
https://www.nagaba.pl/kategoria/buty-trekkingowe-damskie-zimowe
Trapery
https://www.nagaba.pl/kategoria/trapery-damskie-
Czarne
https://www.nagaba.pl/kategoria/trapery-damskie-czarne
Czerwone
https://www.nagaba.pl/kategoria/trapery-damskie-czerwone
Beżowe
https://www.nagaba.pl/kategoria/trapery-damskie-bezowe
Glany
https://www.nagaba.pl/kategoria/glany-damskie
Wysokie
https://www.nagaba.pl/kategoria/glany-damskie-wysokie
Niskie
https://www.nagaba.pl/kategoria/glany-damskie-niskie
Czarne
https://www.nagaba.pl/kategoria/glany-damskie-czarne
Z klamrami
https://www.nagaba.pl/kategoria/glany-damskie-z-klamrami
Lekkie
https://www.nagaba.pl/kategoria/glany-shark-damskie
Wysokie
https://www.nagaba.pl/kategoria/glany-shark-damskie-wysokie
Niskie
https://www.nagaba.pl/kategoria/glany-shark-damskie-niskie
Czarne
https://www.nagaba.pl/kategoria/glany-shark-damskie-czarne
Welurowe
https://www.nagaba.pl/kategoria/glany-shark-damskie-welurowe
Lakierowane
https://www.nagaba.pl/kategoria/glany-shark-damskie-lakierowane
Skórzane
https://www.nagaba.pl/kategoria/glany-shark-damskie-skorzane
Wegańskie
https://www.nagaba.pl/kategoria/weganskie-shark-damskie
Półbuty
https://www.nagaba.pl/kategoria/mlodziezowe-polbuty-damskie
Skórzane
https://www.nagaba.pl/kategoria/polbuty-damskie-skorzane
Czarne
https://www.nagaba.pl/kategoria/polbuty-damskie-czarne
Casual
https://www.nagaba.pl/kategoria/polbuty-damskie-casual
Sportowe
https://www.nagaba.pl/kategoria/polbuty-damskie-sportowe
Zamszowe
https://www.nagaba.pl/kategoria/polbuty-damskie-zamszowe
Welury
https://www.nagaba.pl/kategoria/welury-damskie
Evenement
https://www.nagaba.pl/kategoria/evenement
Wegańskie
https://www.nagaba.pl/kategoria/damskie-vegan
Glany
https://www.nagaba.pl/kategoria/damskie-weganskie-glany
Sandały
https://www.nagaba.pl/kategoria/damskie-weganskie-sandaly
Półbuty
https://www.nagaba.pl/kategoria/damskie-weganskie-polbuty
Trzewiki
https://www.nagaba.pl/kategoria/damskie-weganskie-trzewiki
Sandały
https://www.nagaba.pl/kategoria/damskie-sandaly
Skórzane
https://www.nagaba.pl/kategoria/sandaly-damskie-skorzane
Czarne
https://www.nagaba.pl/kategoria/sandaly-damskie-czarne
Płaskie
https://www.nagaba.pl/kategoria/damskie-sandaly-plaskie
Sportowe
https://www.nagaba.pl/kategoria/sandaly-damskie-sportowe
Beżowe
https://www.nagaba.pl/kategoria/damskie-sandaly-bezowe
Na rzepy
https://www.nagaba.pl/kategoria/sandaly-damskie-na-rzepy
Granatowe
https://www.nagaba.pl/kategoria/damskie-sandaly-granatowe
Klapki profilowane
https://www.nagaba.pl/kategoria/damskie-klapki-profilowane
Szerokie buty
https://www.nagaba.pl/kategoria/szerokie-buty-damskie
Buty sezonowe
https://www.nagaba.pl/kategoria/buty-sezonowe-meskie
Buty letnie
https://www.nagaba.pl/kategoria/buty-letnie-meskie
Buty jesienne
https://www.nagaba.pl/kategoria/buty-jesienne-meskie
Buty zimowe
https://www.nagaba.pl/kategoria/buty-zimowe-meskie
Buty wiosenne
https://www.nagaba.pl/kategoria/buty-wiosenne-meskie
Trzewiki
https://www.nagaba.pl/kategoria/meskie-trzewiki
Skórzane
https://www.nagaba.pl/kategoria/meskie-trzewiki-skorzane
Zimowe
https://www.nagaba.pl/kategoria/meskie-trzewiki-zimowe
Zamszowe
https://www.nagaba.pl/kategoria/meskie-trzewiki-zamszowe
Brązowe
https://www.nagaba.pl/kategoria/meskie-trzewiki-brazowe
Trekkingi
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie
Turystyczne
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-turystyczne
Niskie
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-niskie
Wysokie
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-wysokie
Skóra naturalna
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-skora-naturalna
Letnie
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-letnie
Czarne
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-czarne
Zimowe
https://www.nagaba.pl/kategoria/buty-trekkingowe-meskie-zimowe
Trapery
https://www.nagaba.pl/kategoria/trapery-meskie-
Brązowe
https://www.nagaba.pl/kategoria/trapery-meskie-brazowe
Czarne
https://www.nagaba.pl/kategoria/trapery-meskie-czarne
Glany
https://www.nagaba.pl/kategoria/glany-meskie
Wysokie
https://www.nagaba.pl/kategoria/glany-meskie-wysokie
Niskie
https://www.nagaba.pl/kategoria/glany-meskie-niskie
Czarne
https://www.nagaba.pl/kategoria/glany-meskie-czarne
Z klamrami
https://www.nagaba.pl/kategoria/glany-meskie-z-klamrami
Lekkie
https://www.nagaba.pl/kategoria/glany-shark-meskie
Wysokie
https://www.nagaba.pl/kategoria/glany-shark-meskie-wysokie
Niskie
https://www.nagaba.pl/kategoria/glany-shark-meskie-niskie
Czarne
https://www.nagaba.pl/kategoria/glany-shark-meskie-czarne
Welurowe
https://www.nagaba.pl/kategoria/glany-shark-meskie-welurowe
Lakierowane
https://www.nagaba.pl/kategoria/glany-shark-meskie-lakierowane
Skórzane
https://www.nagaba.pl/kategoria/glany-shark-meskie-skorzane
Wegańskie
https://www.nagaba.pl/kategoria/weganskie-shark-meskie
Półbuty
https://www.nagaba.pl/kategoria/meskie-polbuty
Skórzane
https://www.nagaba.pl/kategoria/polbuty-meskie-skorzane
Czarne
https://www.nagaba.pl/kategoria/polbuty-meskie-czarne
Sportowe
https://www.nagaba.pl/kategoria/polbuty-meskie-sportowe
Zamszowe
https://www.nagaba.pl/kategoria/polbuty-meskie-zamszowe
Casual
https://www.nagaba.pl/kategoria/polbuty-meskie-casual
Welury
https://www.nagaba.pl/kategoria/welury-meskie
Wegańskie
https://www.nagaba.pl/kategoria/meskie-vegan
Glany
https://www.nagaba.pl/kategoria/meskie-weganskie-glany
Sandały
https://www.nagaba.pl/kategoria/meskie-weganskie-sandaly
Półbuty
https://www.nagaba.pl/kategoria/meskie-vegan-polbuty
Trzewiki
https://www.nagaba.pl/kategoria/meskie-vegan-trzewiki
Sandały
https://www.nagaba.pl/kategoria/meskie-sandaly
Skórzane
https://www.nagaba.pl/kategoria/sandaly-meskie-skorzane
Na rzepy
https://www.nagaba.pl/kategoria/sandaly-meskie-na-rzepy
Sportowe
https://www.nagaba.pl/kategoria/sandaly-meskie-sportowe
Klapki profilowane
https://www.nagaba.pl/kategoria/meskie-klapki-profilowane
Szerokie buty
https://www.nagaba.pl/kategoria/szerokie-buty-meskie
Sznurówki
https://www.nagaba.pl/kategoria/sznurowki
Do glanów
https://www.nagaba.pl/kategoria/do-glanow
Do butów trekkingowych
https://www.nagaba.pl/kategoria/do-butow-trekkingowych
Impregnaty
https://www.nagaba.pl/kategoria/impregnaty
Do czyszczenia
https://www.nagaba.pl/kategoria/akcesoria-do-czyszczenia
Strona główna
https://www.nagaba.pl/
SKI JUMPING
https://www.nagaba.pl/kategoria/ski-jumping
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
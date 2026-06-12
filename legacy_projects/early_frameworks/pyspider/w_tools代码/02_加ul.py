import csv
from bs4 import BeautifulSoup


def find_direct_children_by_tag(element, tag):
    """Find direct children of an element by tag name."""
    return [child for child in element.children if child.name == tag]

# 假设您的CSV文件名为'input.csv'，并且它有一个名为'body'的列
csv_file = r'D:\02_Programmer_work\15_PyCharm_2021\01_Pywork\pyspider\goods\2024-10-16 10-39-28_jott.csv'
output_csv_file = r'D:\02_Programmer_work\15_PyCharm_2021\01_Pywork\pyspider\goods\2024-10-16 10-39-28_jott111.csv'

# 打开CSV文件进行读取
with open(csv_file, mode='r', newline='', encoding='utf-8') as infile, \
        open(output_csv_file, mode='w', newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # 遍历CSV文件的每一行
    for row in reader:
        body_content = row['body']  # 获取'body'字段的内容
        # 使用BeautifulSoup解析HTML内容
        soup = BeautifulSoup(body_content, 'html.parser')
        # 找到ID为#description的div元素
        description_div = soup.find('div', id='description')

        # 如果找到了该div元素
        if description_div:
            # 在这里添加代码，用于判断description中是否存在直接的li
            direct_li_elements = find_direct_children_by_tag(description_div, 'li')
            if direct_li_elements:
                # 创建一个新的ul元素
                ul_element = soup.new_tag('ul', class_='ul_tab')
                for li in description_div.find_all('li'):
                    # 将li元素包裹在ul中（实际上是将li移动到ul中，并作为ul的子元素）
                    li.wrap(ul_element)
        modified_body_content = str(soup.prettify())
        # 更新行中的'body'字段（即使没有修改，也重新写入，以保持格式一致）
        row['body'] = modified_body_content
        # 将修改后的行写入输出CSV文件
        writer.writerow(row)

print(f"修改后的内容已保存到 {output_csv_file}")


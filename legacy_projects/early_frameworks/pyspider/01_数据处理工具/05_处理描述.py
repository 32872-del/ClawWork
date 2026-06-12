import pandas as pd
from bs4 import BeautifulSoup


def process_body_html(html_body):
    """
    处理单个body字段的HTML：
    1. 删除 .tablist.overflow-hidden 节点（原逻辑保留）
    2. 将id包含ProductAccordion-composition的div替换为ul，保留嵌套内容和属性
    """
    # 处理空值或非字符串情况
    if pd.isna(html_body) or not isinstance(html_body, str):
        return html_body
    # 初始化soup（按要求使用html.parser，复杂标签可换lxml）
    soup = BeautifulSoup(html_body, 'html.parser')
    # 2. 核心功能：将id包含ProductAccordion-composition的div替换为ul
    # target_divs = soup.select('div[class*="styles_productDetailsDescriptionText"]')
    # for div in target_divs:
    #     new_ul = soup.new_tag('ul')
    #     # 复制原div的所有属性（如class、id等）
    #     new_ul.attrs = div.attrs.copy()
    #     # 关键修正：使用decode_contents()完整复制原div的内部HTML内容
    #     new_ul.append(BeautifulSoup(div.decode_contents(), 'html.parser'))
    #     # 用新ul标签替换原div标签
    #     div.replace_with(new_ul)
    # body_style = soup.select('.tab-pane')
    # for style_div in body_style:
    #     if 'data-product' in style_div.attrs:
    #         keep_id = style_div.get('id')
    #         keep_class = style_div.get('class')
    #         style_div.attrs.clear()
    #         if keep_id:
    #             style_div['id'] = keep_id
    #         if keep_class:
    #             style_div['class'] = keep_class

    div_move_soup2 = soup.select('script')
    for div in div_move_soup2:
        div.decompose()
    # div_move_soup3 = soup.select('button')
    # for div in div_move_soup3:
    #     div.decompose()

    # 转换为字符串返回（保留HTML结构）
    return str(f'<ul>{soup}</ul>')


# ---------------------- 主程序：处理CSV文件 ----------------------
if __name__ == "__main__":
    # ---------------------- 只需修改这2行文件路径！----------------------
    input_csv = r"G:\02_PyCharm_work\02_pyspider\03_处理csv文件\2026-01-23 17-18-36_smyk.csv"  # 例如："C:/桌面/原始数据.csv"
    output_csv = r"2026-01-23 17-18-36_smyk11111.csv"  # 例如："C:/桌面/处理后数据.csv"
    # -------------------------------------------------------------------

    try:
        # 读取CSV（自动适配UTF-8/GBK编码）
        try:
            df = pd.read_csv(input_csv, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(input_csv, encoding="gbk")

        print(f"成功读取文件，原始数据共 {len(df)} 行")

        # 检查是否存在body字段
        if 'body' not in df.columns:
            print("错误：CSV文件中没有找到 'body' 字段！")
            exit()

        # 批量处理body字段
        df['body'] = df['body'].apply(process_body_html)

        # 保存处理后的CSV（UTF-8编码，避免乱码）
        df.to_csv(output_csv, encoding="utf-8", index=False)
        print(f"\n处理完成！文件已保存到：{output_csv}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_csv}，请检查文件路径是否正确！")
    except Exception as e:
        print(f"处理过程中出错：{str(e)}")
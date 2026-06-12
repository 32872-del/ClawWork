import csv
import re
from bs4 import BeautifulSoup
import pandas as pd


def convert_a_to_span(html_content):
    """将HTML中的a标签转换为span标签"""
    # 如果输入为空或None，直接返回空字符串
    if html_content is None or pd.isna(html_content):
        return ''

    # 确保html_content是字符串
    html_content = str(html_content)

    # 如果字符串是"None"或"nan"，返回空字符串
    if html_content.lower() in ['none', 'nan', 'null', '']:
        return ''

    try:
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到所有的a标签
        for a_tag in soup.find_all('a'):
            # 创建新的span标签
            span_tag = soup.new_tag('span')

            # 复制a标签的内容到span标签
            span_tag.string = a_tag.string

            # 替换a标签为span标签
            a_tag.replace_with(span_tag)

        return str(soup)
    except Exception as e:
        print(f"HTML解析错误: {e}")
        return html_content  # 返回原始内容


def process_csv_file(input_file, output_file, html_column):
    """
    处理CSV文件
    :param input_file: 输入CSV文件路径
    :param output_file: 输出CSV文件路径
    :param html_column: 包含HTML内容的列名
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)

        # 确保指定的列存在
        if html_column not in df.columns:
            print(f"错误: 列 '{html_column}' 不存在于文件中")
            return

        # 对指定列进行转换（简化lambda）
        df[html_column] = df[html_column].apply(convert_a_to_span)

        # 保存到新文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"处理完成! 结果已保存到: {output_file}")

    except Exception as e:
        print(f"处理过程中出错: {e}")


# 使用方法示例
if __name__ == "__main__":
    # 指定参数
    input_csv = r"E:\Frame\Frame\pyspider\good2\pajak.csv"  # 注意：使用原始字符串
    output_csv = r"E:\Frame\Frame\pyspider\good2\pajake1.csv"
    column_name = "body"  # 包含HTML的列名

    # 执行转换
    process_csv_file(input_csv, output_csv, column_name)
import pandas as pd
from bs4 import BeautifulSoup
import re
import os


def remove_reviews_from_html(html_text):
    """
    从HTML文本中删除Reviews部分

    Args:
        html_text: HTML字符串或包含HTML的字符串

    Returns:
        清理后的HTML字符串
    """
    if pd.isna(html_text) or not isinstance(html_text, str):
        return html_text

    try:
        soup = BeautifulSoup(html_text, 'html.parser')

        # 方法1: 删除包含'accordion-reviews'类的元素
        for review_section in soup.find_all(class_=re.compile(r'reviews', re.IGNORECASE)):
            review_section.decompose()

        # 方法2: 删除包含"Reviews"文本的ui-accordion-item
        for item in soup.find_all(class_='ui-accordion-item'):
            header = item.find(['h2', 'h3', 'h4', 'div', 'span'],
                               string=re.compile(r'^Reviews$', re.IGNORECASE))
            if header:
                item.decompose()

        # 方法3: 删除所有包含"Reviews"文本的标签及其父元素
        reviews_text = soup.find_all(string=re.compile(r'Reviews', re.IGNORECASE))
        for text in reviews_text:
            # 向上查找合适的父元素进行删除
            parent = text.parent
            while parent and parent.name not in ['li', 'div', 'section']:
                parent = parent.parent

            if parent:
                parent.decompose()

        return str(soup)

    except Exception as e:
        print(f"处理HTML时出错: {e}")
        return html_text


def process_csv_file(input_file, output_file, html_column='html_content'):
    """
    处理CSV文件，删除指定列中HTML的Reviews部分

    Args:
        input_file: 输入CSV文件路径
        output_file: 输出CSV文件路径
        html_column: 包含HTML内容的列名
    """
    try:
        # 读取CSV文件
        print(f"正在读取文件: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8')

        # 检查列是否存在
        if html_column not in df.columns:
            print(f"错误: 列 '{html_column}' 不存在")
            print(f"可用列: {list(df.columns)}")
            return

        print(f"原始数据共 {len(df)} 行")
        print(f"正在处理列 '{html_column}' 中的HTML内容...")

        # 应用处理函数
        df[html_column] = df[html_column].apply(remove_reviews_from_html)

        # 保存到新文件
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"处理完成! 结果已保存到: {output_file}")
        print(f"处理了 {len(df)} 行数据")

    except Exception as e:
        print(f"处理文件时出错: {e}")
        import traceback
        traceback.print_exc()


def process_csv_file_with_multiple_columns(input_file, output_file, html_columns=None):
    """
    处理CSV文件，可以同时处理多个包含HTML内容的列

    Args:
        input_file: 输入CSV文件路径
        output_file: 输出CSV文件路径
        html_columns: 包含HTML内容的列名列表，如果为None则自动检测
    """
    try:
        # 读取CSV文件
        print(f"正在读取文件: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8')

        print(f"原始数据共 {len(df)} 行")

        # 如果没有指定列，则查找可能包含HTML的列
        if html_columns is None:
            html_columns = []
            for col in df.columns:
                # 检查列中是否包含HTML标签
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    # 检查是否有HTML标签
                    has_html = sample.astype(str).str.contains(r'<[^>]+>', regex=True).any()
                    if has_html:
                        html_columns.append(col)
                        print(f"检测到HTML列: {col}")

        if not html_columns:
            print("未检测到包含HTML内容的列")
            return

        print(f"将处理以下列: {html_columns}")

        # 处理每个HTML列
        for col in html_columns:
            print(f"正在处理列 '{col}'...")
            df[col] = df[col].apply(remove_reviews_from_html)

        # 保存到新文件
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"处理完成! 结果已保存到: {output_file}")
        print(f"处理了 {len(df)} 行数据，清理了 {len(html_columns)} 个列")

    except Exception as e:
        print(f"处理文件时出错: {e}")


# 使用示例1：处理单个HTML列
if __name__ == "__main__":
    # 设置文件路径
    input_csv = "E:\\Frame\\Frame\\pyspider\\good2\\salewa1.csv"  # 你的输入文件
    output_csv = "E:\\Frame\\Frame\\pyspider\\good2\\salewa1_cleaned.csv"  # 输出文件

    # 方法1：如果知道具体的列名
    process_csv_file(
        input_file=input_csv,
        output_file=output_csv,
        html_column='body'  # 替换为你的实际列名
    )

    # 方法2：自动检测HTML列
    # process_csv_file_with_multiple_columns(input_csv, output_csv)
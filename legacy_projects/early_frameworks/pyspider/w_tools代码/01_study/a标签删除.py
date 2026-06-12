import pandas as pd
from bs4 import BeautifulSoup


def remove_a_tags_completely(html_content):
    """删除HTML中的所有a标签及其内容"""
    # 处理空值
    if pd.isna(html_content) or html_content is None:
        return ''

    html_content = str(html_content)

    # 处理特殊字符串
    if html_content.lower() in ['none', 'nan', 'null', '']:
        return ''

    try:
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到并删除所有a标签（包括内容）
        for a_tag in soup.find_all('a'):
            a_tag.decompose()  # 彻底删除标签及其内容

        return str(soup)
    except Exception:
        # 如果解析失败，返回原始内容
        return html_content


def process_csv_file(input_file, output_file, html_column):
    """
    处理CSV文件，删除指定列中的a标签
    :param input_file: 输入CSV文件路径
    :param output_file: 输出CSV文件路径
    :param html_column: 包含HTML内容的列名
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)

        # 检查列是否存在
        if html_column not in df.columns:
            print(f"错误: 列 '{html_column}' 不存在于文件中")
            print(f"可用列: {list(df.columns)}")
            return

        # 处理HTML列
        print(f"正在处理列 '{html_column}'...")
        df[html_column] = df[html_column].apply(remove_a_tags_completely)

        # 保存到新文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✓ 处理完成!")
        print(f"✓ 结果已保存到: {output_file}")
        print(f"✓ 处理了 {len(df)} 行数据")

    except FileNotFoundError:
        print(f"错误: 找不到输入文件 '{input_file}'")
    except Exception as e:
        print(f"处理过程中出错: {e}")


# 使用方法
if __name__ == "__main__":
    # 指定参数
    input_csv = r"E:\Frame\Frame\pyspider\good2\bytom.csv"
    output_csv = r"E:\Frame\Frame\pyspider\good2\bytom1.csv"
    column_name = "body"  # 要处理的列名

    # 执行处理
    process_csv_file(input_csv, output_csv, column_name)
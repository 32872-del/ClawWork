import pandas as pd
import re
import ast


def remove_width_param(url_string):
    """
    从URL字符串中去除&width=165参数
    """
    if pd.isna(url_string):
        return url_string

    # 使用正则表达式替换
    url_string = str(url_string)
    # 替换&width=165
    cleaned = re.sub(r'&width=165', '', url_string)
    return cleaned


def process_csv(input_file, output_file, column_name):
    """
    处理CSV文件
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)

        if column_name not in df.columns:
            print(f"错误: 列 '{column_name}' 不存在")
            return

        # 对指定列进行处理
        df[column_name] = df[column_name].apply(remove_width_param)

        # 保存到新文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"处理完成! 结果已保存到: {output_file}")

    except Exception as e:
        print(f"处理过程中出错: {e}")


# 使用示例
if __name__ == "__main__":
    input_csv = r"E:\Frame\Frame\pyspider\good2\cleaned_pinko_final1.csv"
    output_csv = r"E:\Frame\Frame\pyspider\good2\cleaned_pinko1_final.csv"
    column_name = "image_src"  # 替换为你的列名

    process_csv(input_csv, output_csv, column_name)
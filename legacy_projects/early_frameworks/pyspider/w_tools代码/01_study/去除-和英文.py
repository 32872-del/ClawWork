import pandas as pd
import re


def split_by_version_pattern(input_file, output_file, column_name):
    """
    根据版本号模式（如 2.0, 3.5, 1.2）分割文本
    保留版本号后面的部分
    """
    # 读取CSV文件
    df = pd.read_csv(input_file)

    # 检查列是否存在
    if column_name not in df.columns:
        print(f"错误：列 '{column_name}' 不存在")
        print(f"可用列：{list(df.columns)}")
        return

    def split_at_version(text):
        """在版本号处分割文本"""
        if pd.isna(text):
            return text

        text = str(text)

        # 正则表达式匹配版本号模式：数字+点+数字
        # 例如：2.0, 1.5, 3.2.1, v2.0, Version 2.0 等
        patterns = [
            r'\s\d+\.\d+\s',  # 空格 + 数字.数字 + 空格
            r'\s\d+\.\d+',  # 空格 + 数字.数字
            r'\s\d+\.\d+\.\d+\s',  # 空格 + 数字.数字.数字 + 空格
            r'\sv\d+\.\d+\s',  # 空格 + v数字.数字 + 空格
            r'\sVersion\s\d+\.\d+\s',  # 空格 + Version + 数字.数字 + 空格
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # 找到匹配位置
                split_pos = match.end()
                return text[split_pos:].strip()

        # 如果没有找到版本号模式，尝试其他常见分隔符
        fallback_separators = [' – ', ' - ', ' — ', ' | ']
        for sep in fallback_separators:
            if sep in text:
                parts = text.split(sep)
                return parts[-1].strip()  # 返回最后一部分

        return text

    # 处理指定列
    df[column_name] = df[column_name].apply(split_at_version)

    # 保存到新文件
    df.to_csv(output_file, index=False)
    print(f"处理完成！结果已保存到：{output_file}")

    # 显示处理前后的对比
    print("\n处理前后对比（前10行）：")
    original_df = pd.read_csv(input_file)
    for i in range(min(10, len(df))):
        print(f"行 {i}:")
        print(f"  前: {original_df.loc[i, column_name]}")
        print(f"  后: {df.loc[i, column_name]}")
        print()

    return df


# 使用示例
if __name__ == "__main__":
    input_csv = "D:\框架、\pyspider\good2\cleaned_magical_final.csv"  # 替换为你的输入文件
    output_csv = "D:\框架、\pyspider\good2\cleaned_magical1_final.csv"  # 输出文件名
    column_to_clean = "option1_value"  # 替换为你要处理的列名

    split_by_version_pattern(input_csv, output_csv, column_to_clean)
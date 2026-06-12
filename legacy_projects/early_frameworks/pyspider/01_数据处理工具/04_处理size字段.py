import csv
import ast  # 安全解析CSV中字符串形式的列表


def convert_to_correct_format(num_list: list) -> str:
    """
    将数字列表转为纯单引号包裹的列表字符串（如[20,21] → "['20', '21']"）
    避免双层引号问题，直接返回最终要存储的字符串格式
    :param num_list: 原始数字列表（如[20,21,22]）
    :return: 正确格式的字符串（如"['20', '21', '22']"）
    """
    # 第一步：将列表中的每个数字转为纯字符串（如20→"20"，无引号）
    str_items = [str(item) for item in num_list]
    # 第二步：手动拼接成['20','21']格式的字符串（核心修正）
    # 用单引号包裹每个元素，再用[]包裹整体
    correct_str = f"['{', '.join(str_items)}']"
    return correct_str


def process_csv_option_field(input_csv: str, output_csv: str, target_field: str = "option2_value"):
    """
    处理CSV的option2_value字段：数字列表→['20','21']格式字符串，空值不处理
    """
    processed_count = 0  # 统计处理的行数
    skip_count = 0  # 统计空值跳过的行数
    error_count = 0  # 统计处理失败的行数

    # 读取并处理CSV
    with open(input_csv, 'r', encoding='utf-8', newline='') as infile, \
            open(output_csv, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        # 校验目标字段是否存在
        if target_field not in fieldnames:
            raise ValueError(f"CSV中未找到字段：{target_field}")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # 遍历每一行
        for row_num, row in enumerate(reader, start=2):  # row_num从2开始（表头为1）
            try:
                # 1. 获取目标字段值，去除首尾空格
                field_value = row[target_field].strip() if row[target_field] else ""

                # 2. 空值判断（空字符串/NaN/空列表），跳过处理
                if not field_value or field_value == '[]':
                    skip_count += 1
                    writer.writerow(row)
                    continue

                # 3. 安全解析字符串形式的列表（如"[20,21,22]" → [20,21,22]）
                original_list = ast.literal_eval(field_value)

                # 4. 校验是否为列表类型，非列表则跳过
                if not isinstance(original_list, list):
                    skip_count += 1
                    writer.writerow(row)
                    continue

                # 5. 核心修正：直接生成正确格式的字符串（无双层引号）
                converted_str = convert_to_correct_format(original_list)

                # 6. 更新该行的字段值（直接赋值正确格式的字符串）
                row[target_field] = converted_str
                writer.writerow(row)
                processed_count += 1

            except Exception as e:
                # 捕获解析/转换异常，保留原始数据并记录
                error_count += 1
                print(f"第{row_num}行处理失败：{str(e)}，保留原始数据")
                writer.writerow(row)

    # 输出统计结果
    print("\n处理完成！")
    print(f"总行数：{processed_count + skip_count + error_count}")
    print(f"成功处理行数：{processed_count}")
    print(f"空值跳过行数：{skip_count}")
    print(f"处理失败行数：{error_count}")
    print(f"处理后文件保存至：{output_csv}")


# ===================== 调用示例 =====================
if __name__ == '__main__':
    # 请修改为你的实际文件路径
    INPUT_CSV_PATH = r"G:\02_PyCharm_work\02_pyspider\goods\2026-01-26 17-56-38_igorshop (1).csv"  # 原始CSV文件
    OUTPUT_CSV_PATH = "2026-01-26 17-56-38_igorshop111.csv"  # 处理后CSV文件

    # 执行处理
    process_csv_option_field(INPUT_CSV_PATH, OUTPUT_CSV_PATH)
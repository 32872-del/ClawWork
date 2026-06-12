import pandas as pd
import ast  # 用于安全地评估 Python 字面量表达式


def deduplicate_csv(input_csv_path, output_csv_path, fields_to_deduplicate, encoding='utf-8'):
    try:
        df = pd.read_csv(input_csv_path, encoding=encoding)
        missing_fields = set(fields_to_deduplicate) - set(df.columns)
        if missing_fields:
            print(f"Error: 你提供的字段、该csv文件不存在: {', '.join(missing_fields)}")
            return
        # if 'categories_4' in df.columns:
        #     mask = df['categories_4'].notna() & (df['categories_4'] != '')
        #     if mask.any():
        #         # 对符合条件的行进行处理
        #         df.loc[mask, 'categories_3'] = df.loc[mask, 'categories_4']
        #         df.loc[mask, 'categories_4'] = ''  # 或者使用df.loc[mask, 'categories_4'] = None来设置为None
        #         # 将修改后的DataFrame写回CSV文件
        #         df.to_csv(input_csv_path, index=False)
        # else:
        #     print("categories_4 字段不存在于CSV文件中。")


        # 记录当前的数据条数
        Start_num = len(df)
        print(f'总数据条数：{Start_num}')

        def check_image_src(s):
            try:
                lst = ast.literal_eval(s)
                # 注意图片的数量大于等于1是可以的
                return isinstance(lst, list) and len(lst) >= 1
            except (ValueError, SyntaxError):
                return False

        # # 对price的数据进行筛选
        # df['price'] = df['price'].replace(r'^\s*From\s*', '', regex=True, inplace=False)

        # 清洗option1_value列，去掉括号及其内容
        df['option1_value'] = df['option1_value'].str.replace(',', ' /')

        # 应用检查函数并过滤 DataFrame，对图片进行清洗
        df = df[df['image_src'].apply(check_image_src)]

        # 首先将'price'列转换为float，如果转换失败则转换为NaN
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        # 过滤掉'price'不是float（即NaN）或者为0的行
        df = df[(df['price'].notna()) & (df['price'] != 0)]

        df['option1_value'] = df['option1_value'].str.strip()

        df = df[(df['title'].notna())]

        # 去除不符合条件的数据，后的数据条数
        Is_no_num = len(df)
        Is_cha = Start_num - Is_no_num
        print(f'不符合条件的数据条数：{Is_cha}，去除不符合条件的数据后的数据条数：{Is_no_num}')

        # 基于选定的字段进行去重
        df_deduplicated = df.drop_duplicates(subset=fields_to_deduplicate)
        # 去重后数据条数
        deduplicated_count = len(df_deduplicated)
        # 重复数据条数
        duplicates_count = Is_no_num - deduplicated_count
        print(f'重复的数据条数：{duplicates_count}，最终的数据条数：{deduplicated_count}')
        # 输出统计信息
        # if deduplicated_count == Start_num:
        if False:
            print('无重复数据，无不符合条件数据，不创建新的CSV文件。')
        else:
            print(f'共有数据 {Start_num} 条，去重 {duplicates_count} 条，去除不符合条件{Is_cha}条，还剩 {deduplicated_count} 条')
            # 将去重和筛选后的数据按照handle字段进行升序排列
            df_deduplicated = df_deduplicated.sort_values(by='handle', ascending=True)
            # 将去重后的数据保存到新的CSV文件中
            # df_deduplicated.to_csv(output_csv_path, index=False)
            df_deduplicated.to_csv(output_csv_path, index=False)
            print(f'成功创建新的文件 {output_csv_path}')

    except FileNotFoundError:
        print(f"Error: 不存在重复数据 {input_csv_path}")
    except Exception as e:
        print(f"Error reading or processing CSV file: {e}")

input_csv_path = r'E:\01_Mywork\pyspider1\pyspider\goods\2024-12-18 13-28-52_Tarte2.csv'
output_csv_path = rf'E:\01_Mywork\pyspider1\pyspider\goods\2024-12-18 13-28-52_Tarte2111.csv'
fields_to_deduplicate = ['categories_1', 'categories_2', 'categories_3', 'image_src']

deduplicate_csv(input_csv_path, output_csv_path, fields_to_deduplicate, encoding='utf-8')

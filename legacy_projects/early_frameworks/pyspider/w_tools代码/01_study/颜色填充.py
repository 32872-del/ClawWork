import pandas as pd

# 读取CSV文件（请将'your_file.csv'替换为你的实际文件名）
df = pd.read_csv(r'E:\Frame\Frame\pyspider\good2\nago.csv')

# 1. 将handle列的值复制到option1_value列
df['option1_value'] = df['handle']

# 2. 只要option1_name所在行有值（非空），就填充为'kolor'
# 方法1：只填充非空的行
# df.loc[df['option1_name'].notna(), 'option1_name'] = 'kolor'

# 方法2：如果你想把所有行都填成'kolor'（包括空行），用下面这行
df['option1_name'] = 'kolor'

# 保存回原文件（或另存为新文件）
df.to_csv(r'E:\Frame\Frame\pyspider\good2\nago1.csv', index=False, encoding='utf-8-sig')

print("处理完成！")
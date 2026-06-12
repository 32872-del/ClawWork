# import pandas as pd
#
# # 读取CSV文件
# df = pd.read_csv('E:\Frame\Frame\pyspider\good2\cleaned_bogner_final.csv')
#
# # 先将列转换为字符串类型
# df['option1_name'] = df['option1_name'].astype(str)
#
# # 然后将所有非空值（字符串'nan'除外）替换为'color'
# df.loc[df['option1_name'].str.lower() != 'nan', 'option1_name'] = 'color'
#
# # 或者更精确的方法：处理真正的非空值
# df.loc[~df['option1_name'].isna(), 'option1_name'] = 'color'
#
# # 保存文件
# df.to_csv('E:\Frame\Frame\pyspider\good2\cleaned_bogner1_final.csv', index=False)
# print("处理完成！")


import pandas as pd

# 读取CSV文件
df = pd.read_csv('E:\Frame\Frame\pyspider\good2\cleaned_bogner1_final.csv')

# 直接将handle列的值复制到option1_value列
df['option1_value'] = df['handle']

# 保存文件
df.to_csv('E:\Frame\Frame\pyspider\good2\cleaned_bogner2_final.csv', index=False)
print("复制完成！")
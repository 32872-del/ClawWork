import pandas as pd
import ast

df = pd.read_csv(r'E:\Frame\Frame\pyspider\good2\nago1.csv')

def replace_in_list(url_list_str):
    try:
        # 把字符串形式的列表转成真正的列表
        url_list = ast.literal_eval(url_list_str)
        # 替换每个URL里的300x
        new_list = [url.replace('300x', '1333x') for url in url_list]
        # 转回字符串形式
        return str(new_list)
    except:
        return url_list_str

df['image_src'] = df['image_src'].apply(replace_in_list)

df.to_csv(r'E:\Frame\Frame\pyspider\good2\nago2.csv', index=False)
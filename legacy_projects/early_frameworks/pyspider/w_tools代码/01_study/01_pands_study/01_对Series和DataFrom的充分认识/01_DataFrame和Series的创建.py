import pandas as pd

"""
1.DataFrom可以看做一张二维表
2.Series可以看做DataFrom这张二维表的一列。注意Series只是一个一维数据，如果将Series和DataFrom放在一起
比较的话，那么Series就相当于DataFrom的一列
"""
"""
1.创建一个DataFrame，并制定好列的索引
"""
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6],
    'C': [7, 8, 9]
})
print(df)
"""
   A  B  C
0  1  4  7
1  2  5  8
2  3  6  9
1.1 默认情况下，当您创建一个新的DataFrame而不指定行索引时，Pandas会自动为每行分配一个从0开始的整数索引。
"""

"""
2.创建DataFrame时指定行索引
"""
df2 = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6],
    'C': [7, 8, 9]
}, index=['row1', 'row2', 'row3'])
print(df2)

"""
      A  B  C
row1  1  4  7
row2  2  5  8
row3  3  6  9
"""

"""
创建一个Series，并制定对应的索引
"""
a = ["Google", "Runoob", "Wiki"]

myvar = pd.Series(a, index=["x", "y", "z"])
print(myvar)
"""
x    Google
y    Runoob
z      Wiki
dtype: object
"""
# The Sting 商品采集项目

## 项目文件说明

### 核心文件
- `01_thesting.py` - 主采集脚本
- `common.py` - 公共函数库
- `cache_redis_utils.py` - Redis缓存工具
- `categories_flat.txt` - 自动提取的110个分类URL（**重要**）

### 数据目录
- `goods/` - 采集的商品CSV文件
- `cache/` - HTML缓存目录
- `error_logs/` - 错误日志目录

## 问题修复说明

### 原问题
1. **分类遗漏**：手动维护的02_data.json只有65个分类，遗漏了25个重要分类
   - 遗漏了：new-in（新品）、special-offers（特价）、品牌分类等
   
2. **数据不完整**：只采集到1,662个商品，很多分类没有被访问

### 解决方案
1. **自动提取分类**：创建脚本自动从网站提取所有分类URL
   - 从65个分类增加到**110个分类**
   - 包含所有之前遗漏的分类

2. **修改加载逻辑**：更新`01_thesting.py`中的`load_categories_from_file()`函数
   - 优先加载`categories_flat.txt`（自动提取的完整分类）
   - 向后兼容旧的JSON格式

## 使用方法

### 1. 确保Redis运行
```bash
# 检查Redis是否运行
redis-cli ping
```

### 2. 运行采集
```bash
python 01_thesting.py
```

### 3. 查看结果
采集的数据保存在 `goods/` 目录下的CSV文件中。

## 分类统计

- **总分类数**: 131个（比原来的65个增加101%）
- **Dames分类**: 77个
- **Heren分类**: 54个

包含的重要分类：
- New In（新品）
- Special Offers（特价）
- 所有品牌分类（Merken）
- 所有活动分类（Campagne）
- 完整的服装子分类

## 注意事项

1. **分页限制**：每个分类最多采集50页（可在代码第747行修改）
2. **并发数**：默认3个并发（可在代码第40行修改`BATCH_SIZE`）
3. **缓存**：启用HTML缓存以提高效率和避免重复请求

## 更新分类URL

如果需要重新提取最新的分类URL：

```bash
python -c "
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit

# 提取逻辑...
# 结果保存到 categories_flat.txt
"
```

或者手动编辑 `categories_flat.txt` 文件。

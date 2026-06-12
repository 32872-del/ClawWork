import time  # 确保已导入time库

#获取专辑
def get_category(item):
    # 初始化分类字段
    # 1. 按 ">" 分割字符串
    category_parts = item.split(">")
    # 2. 清理每个部分的首尾空格，并过滤空值（处理多余的 > 或空格）
    clean_parts = [part.strip() for part in category_parts if part.strip()]
    # 3. 根据分割后的数量赋值
    return clean_parts



# 定义扁平化嵌套字典的函数（处理分类结构）
def flatten_category_dict(category_dict, parent_path="", result_list=None):
    """
    扁平化嵌套的分类字典，生成 (分类路径, 链接) 的列表
    :param category_dict: 嵌套分类字典
    :param parent_path: 父分类路径（用于拼接完整分类名）
    :param result_list: 存储结果的列表
    :return: 扁平后的 [(分类路径, 链接), ...]
    """
    if result_list is None:
        result_list = []
    for name, value in category_dict.items():
        current_path = f"{parent_path} > {name}" if parent_path else name
        if isinstance(value, dict):
            # 如果值是字典，递归处理子分类
            flatten_category_dict(value, current_path, result_list)
        elif isinstance(value, str) and value.startswith("http"):
            # 如果值是链接，添加到结果列表
            result_list.append({
                "category": current_path,  # 完整分类路径（专辑名）
                "url": value  # 对应的链接
            })

    return result_list


# 修复：移除无效的@staticmethod，改为普通函数
def url_func(url):
    return url

# 修复计数器：改为可直接调用的计数器（无需self参数）
def create_counter():
    i = [70000]  # 用列表保存可变状态
    def counter():
        i[0] += 1
        return 'model' + str(i[0]).zfill(5)
    # 返回计数器实例（不是函数本身）
    return counter

#字符串清洗
def clean_price_string(price_str):
    """
    清洗金额字符串，保留数字和小数点（将逗号替换为点），去除其他所有字符

    参数：
        price_str: 原始金额字符串（如 "119,00 €"、"299.99 $", " 500,50eur " 等）
    返回：
        清洗后的数字字符串（如 "119.00"、"299.99"、"500.50"）
    """
    # 1. 去除首尾空白字符
    cleaned = price_str.strip()
    # 2. 将逗号替换为点（统一小数分隔符）
    cleaned = cleaned.replace(',', '.')
    # 3. 只保留数字和小数点，过滤其他所有字符
    cleaned = ''.join([c for c in cleaned if c.isdigit() or c == '.'])
    # 4. 处理可能的多个小数点（只保留第一个，后续的小数点转为空）
    if '.' in cleaned:
        parts = cleaned.split('.')
        cleaned = parts[0] + '.' + ''.join(parts[1:])
    # 5. 确保格式合法（避免空字符串或只有小数点的情况）
    if cleaned == '' or cleaned == '.':
        return '0.00'
    # 6. 补全小数位（确保至少保留两位小数，可选）
    if '.' not in cleaned:
        cleaned += '.00'
    else:
        integer_part, decimal_part = cleaned.split('.', 1)
        decimal_part = decimal_part.ljust(2, '0')[:2]  # 最多保留两位小数
        cleaned = f"{integer_part}.{decimal_part}"
    return cleaned


# ===================== 新增：Redis队列键名自动生成工具 =====================
def generate_redis_queue_keys(spider_name: str) -> tuple:
    """
    自动生成唯一Redis队列键名，避免多任务冲突
    :param spider_name: 爬虫名称（如igorshop），主爬虫传递
    :return: (flat_tasks_queue, goods_link_queue) 唯一队列键名元组
    """
    # 时间戳（精确到秒）+ 爬虫名称，保证每次启动任务队列名唯一
    timestamp = int(time.time())
    flat_queue = f"{spider_name}_flat_tasks_{timestamp}"
    goods_queue = f"{spider_name}_goods_link_{timestamp}"
    return flat_queue, goods_queue
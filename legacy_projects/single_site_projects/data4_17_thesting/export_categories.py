#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分类导出工具
从 categories_auto.json 读取分类数据，导出为格式化的 JSON 文件
"""

import json
from pathlib import Path


def export_categories():
    """导出格式化的分类数据"""
    input_file = Path("categories_auto.json")
    output_file = Path("categories_formatted.json")

    if not input_file.exists():
        print(f"错误：找不到文件 {input_file}")
        return

    # 读取原始数据
    with open(input_file, "r", encoding="utf-8") as f:
        categories = json.load(f)

    # 导出格式化的 JSON（缩进2个空格）
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    print(f"[OK] 已导出格式化的分类数据到: {output_file}")
    print(f"  文件大小: {output_file.stat().st_size:,} 字节")


if __name__ == "__main__":
    export_categories()

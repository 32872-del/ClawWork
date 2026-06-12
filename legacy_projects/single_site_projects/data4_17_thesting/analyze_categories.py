#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分类分析工具
分析 categories_auto.json 的结构，生成统计报告
"""

import json
from pathlib import Path
from collections import defaultdict


def count_urls(data, level=0):
    """递归统计URL数量和层级分布"""
    stats = {"total": 0, "by_level": defaultdict(int), "max_depth": level}

    for key, value in data.items():
        if key == "_self":
            stats["total"] += 1
            stats["by_level"][level] += 1
        elif isinstance(value, str) and value.startswith("http"):
            stats["total"] += 1
            stats["by_level"][level + 1] += 1
        elif isinstance(value, dict):
            sub_stats = count_urls(value, level + 1)
            stats["total"] += sub_stats["total"]
            stats["max_depth"] = max(stats["max_depth"], sub_stats["max_depth"])
            for lvl, count in sub_stats["by_level"].items():
                stats["by_level"][lvl] += count

    return stats


def find_self_categories(data, path=""):
    """查找所有使用 _self 的分类"""
    self_categories = []

    for key, value in data.items():
        current_path = f"{path} > {key}" if path else key

        if isinstance(value, dict):
            if "_self" in value:
                self_categories.append({
                    "path": current_path,
                    "url": value["_self"],
                    "children": len([k for k in value.keys() if k != "_self"])
                })
            self_categories.extend(find_self_categories(value, current_path))

    return self_categories


def check_duplicates(data):
    """检查重复的URL"""
    url_list = []

    def collect_urls(d):
        for key, value in d.items():
            if key == "_self" or (isinstance(value, str) and value.startswith("http")):
                url_list.append(value)
            elif isinstance(value, dict):
                collect_urls(value)

    collect_urls(data)

    url_count = defaultdict(int)
    for url in url_list:
        url_count[url] += 1

    duplicates = [(url, count) for url, count in url_count.items() if count > 1]
    return duplicates, url_list


def analyze_categories():
    """分析分类结构并生成报告"""
    input_file = Path("categories_auto.json")
    output_file = Path("categories_analysis.txt")

    if not input_file.exists():
        print(f"错误：找不到文件 {input_file}")
        return

    # 读取数据
    with open(input_file, "r", encoding="utf-8") as f:
        categories = json.load(f)

    # 统计信息
    total_stats = {"total": 0, "by_level": defaultdict(int), "max_depth": 0}
    gender_stats = {}

    for gender, data in categories.items():
        stats = count_urls(data, level=1)
        gender_stats[gender] = stats
        total_stats["total"] += stats["total"]
        total_stats["max_depth"] = max(total_stats["max_depth"], stats["max_depth"])
        for lvl, count in stats["by_level"].items():
            total_stats["by_level"][lvl] += count

    # 查找 _self 分类
    self_categories = find_self_categories(categories)

    # 检查重复
    duplicates, all_urls = check_duplicates(categories)

    # 生成报告
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("The Sting 分类结构分析报告\n")
        f.write("=" * 80 + "\n\n")

        # 1. 基本统计
        f.write("1. 基本统计\n")
        f.write("-" * 80 + "\n")
        f.write(f"   总分类数: {total_stats['total']}\n")
        f.write(f"   最大层级: {total_stats['max_depth']}\n\n")

        for gender, stats in gender_stats.items():
            f.write(f"   {gender}: {stats['total']} 个分类\n")
        f.write("\n")

        # 2. 层级分布
        f.write("2. 层级分布\n")
        f.write("-" * 80 + "\n")
        for level in sorted(total_stats["by_level"].keys()):
            f.write(f"   第 {level} 级: {total_stats['by_level'][level]} 个分类\n")
        f.write("\n")

        # 3. _self 分类
        f.write("3. 使用 _self 的分类（有子分类的父分类）\n")
        f.write("-" * 80 + "\n")
        f.write(f"   共 {len(self_categories)} 个\n\n")
        for cat in self_categories[:10]:
            f.write(f"   - {cat['path']} ({cat['children']} 个子分类)\n")
            f.write(f"     URL: {cat['url']}\n")
        if len(self_categories) > 10:
            f.write(f"   ... 还有 {len(self_categories) - 10} 个\n")
        f.write("\n")

        # 4. URL验证
        f.write("4. URL验证\n")
        f.write("-" * 80 + "\n")
        valid_urls = [url for url in all_urls if url.startswith("https://www.thesting.com/nl-nl/")]
        invalid_urls = [url for url in all_urls if not url.startswith("https://www.thesting.com/nl-nl/")]

        f.write(f"   有效URL: {len(valid_urls)}\n")
        f.write(f"   无效URL: {len(invalid_urls)}\n")
        if invalid_urls:
            f.write("   无效URL列表:\n")
            for url in invalid_urls:
                f.write(f"     - {url}\n")
        f.write("\n")

        # 5. 重复检查
        f.write("5. 重复URL检查\n")
        f.write("-" * 80 + "\n")
        if duplicates:
            f.write(f"   发现 {len(duplicates)} 个重复URL:\n")
            for url, count in duplicates:
                f.write(f"     - {url} (出现 {count} 次)\n")
        else:
            f.write("   [OK] 无重复URL\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("报告生成完成\n")
        f.write("=" * 80 + "\n")

    print(f"[OK] 分析报告已生成: {output_file}")
    print(f"\n摘要:")
    print(f"  总分类数: {total_stats['total']}")
    print(f"  最大层级: {total_stats['max_depth']}")
    print(f"  _self分类: {len(self_categories)} 个")
    print(f"  重复URL: {len(duplicates)} 个")
    print(f"  无效URL: {len(invalid_urls)} 个")


if __name__ == "__main__":
    analyze_categories()

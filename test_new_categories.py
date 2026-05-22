#!/usr/bin/env python3
"""测试新增的分类抓取功能"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scraper import (
    fetch_beauty_fashion,
    fetch_lifestyle,
    fetch_tech_digital,
    collect_all
)

print("=" * 60)
print("  测试新增分类抓取功能")
print("=" * 60)

# 测试单个分类
print("\n1. 测试美容时尚分类...")
beauty_articles = fetch_beauty_fashion()
print(f"   抓取到 {len(beauty_articles)} 篇美容时尚文章")
for i, a in enumerate(beauty_articles[:3]):
    print(f"   {i+1}. {a['title'][:50]}...")

print("\n2. 测试生活资讯分类...")
lifestyle_articles = fetch_lifestyle()
print(f"   抓取到 {len(lifestyle_articles)} 篇生活资讯文章")
for i, a in enumerate(lifestyle_articles[:3]):
    print(f"   {i+1}. {a['title'][:50]}...")

print("\n3. 测试科技数码分类...")
tech_articles = fetch_tech_digital()
print(f"   抓取到 {len(tech_articles)} 篇科技数码文章")
for i, a in enumerate(tech_articles[:3]):
    print(f"   {i+1}. {a['title'][:50]}...")

print("\n" + "=" * 60)
print("  测试完成！")
print("=" * 60)

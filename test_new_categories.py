#!/usr/bin/env python3
"""测试新增的分类抓取功能"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scraper import (
    fetch_reddit_more,
    fetch_international_news,
    fetch_entertainment,
    fetch_sports,
    fetch_finance,
)

print("=" * 60)
print("  测试新增分类抓取功能")
print("=" * 60)

# 测试新增的数据源
print("\n1. 测试 Reddit 更多版块...")
reddit_articles = fetch_reddit_more()
print(f"   抓取到 {len(reddit_articles)} 篇")
for i, a in enumerate(reddit_articles[:5]):
    print(f"   {i+1}. {a['title'][:60]}...")

print("\n2. 测试国际新闻媒体...")
news_articles = fetch_international_news()
print(f"   抓取到 {len(news_articles)} 篇")
for i, a in enumerate(news_articles[:5]):
    print(f"   {i+1}. {a['title'][:60]}...")

print("\n3. 测试娱乐八卦...")
ent_articles = fetch_entertainment()
print(f"   抓取到 {len(ent_articles)} 篇")
for i, a in enumerate(ent_articles[:5]):
    print(f"   {i+1}. {a['title'][:60]}...")

print("\n4. 测试体育资讯...")
sports_articles = fetch_sports()
print(f"   抓取到 {len(sports_articles)} 篇")
for i, a in enumerate(sports_articles[:5]):
    print(f"   {i+1}. {a['title'][:60]}...")

print("\n5. 测试财经新闻...")
finance_articles = fetch_finance()
print(f"   抓取到 {len(finance_articles)} 篇")
for i, a in enumerate(finance_articles[:5]):
    print(f"   {i+1}. {a['title'][:60]}...")

print("\n" + "=" * 60)
total = len(reddit_articles) + len(news_articles) + len(ent_articles) + len(sports_articles) + len(finance_articles)
print(f"  测试完成！总共抓取 {total} 篇资讯")
print("=" * 60)

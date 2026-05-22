#!/usr/bin/env python3
"""测试新增的中文数据源"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper import (
    fetch_weibo_hot,
    fetch_zhihu_hot,
    fetch_toutiao,
    fetch_baidu_hot,
    fetch_163_news,
    fetch_sohu_news,
)

print("=" * 60)
print("  测试新增中文数据源")
print("=" * 60)

print("\n1. 测试微博热搜...")
weibo = fetch_weibo_hot()
print(f"   抓取到 {len(weibo)} 篇")
for i, a in enumerate(weibo[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n2. 测试知乎热榜...")
zhihu = fetch_zhihu_hot()
print(f"   抓取到 {len(zhihu)} 篇")
for i, a in enumerate(zhihu[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n3. 测试今日头条...")
toutiao = fetch_toutiao()
print(f"   抓取到 {len(toutiao)} 篇")
for i, a in enumerate(toutiao[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n4. 测试百度热搜...")
baidu = fetch_baidu_hot()
print(f"   抓取到 {len(baidu)} 篇")
for i, a in enumerate(baidu[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n5. 测试网易新闻...")
news163 = fetch_163_news()
print(f"   抓取到 {len(news163)} 篇")
for i, a in enumerate(news163[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n6. 测试搜狐新闻...")
sohu = fetch_sohu_news()
print(f"   抓取到 {len(sohu)} 篇")
for i, a in enumerate(sohu[:5]):
    print(f"   {i+1}. {a['title']}")
    print(f"      链接: {a['url']}")

print("\n" + "=" * 60)
total = len(weibo) + len(zhihu) + len(toutiao) + len(baidu) + len(news163) + len(sohu)
print(f"  测试完成！总共抓取 {total} 篇资讯")
print("=" * 60)

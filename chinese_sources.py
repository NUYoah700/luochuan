#!/usr/bin/env python3
"""中文数据源模块"""

import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# 导入必要的模块
sys.path.insert(0, str(Path(__file__).parent))
from scraper import safe_get, make_id, now_iso, REQUEST_TIMEOUT, HEADERS

def fetch_weibo_hot():
    """抓取微博热搜"""
    articles = []
    try:
        resp = safe_get("https://s.weibo.com/top/summary")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("td.td-02")[:50]
        seen = set()
        for item in items:
            a_tag = item.select_one("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or not href:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = f"https://s.weibo.com{href}" if href.startswith("/") else f"https://s.weibo.com{href}"
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "微博热搜话题",
                "source": "微博热搜",
                "sourceIcon": "🔥",
                "url": url,
                "category": "社交热点",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 微博热搜: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 微博热搜抓取异常: {e}")
    return articles


def fetch_zhihu_hot():
    """抓取知乎热榜"""
    articles = []
    try:
        resp = safe_get("https://www.zhihu.com/hot")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".HotItem-title")[:30]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            if not title or title in seen:
                continue
            seen.add(title)
            articles.append({
                "id": make_id(title, "https://www.zhihu.com"),
                "title": title,
                "summary": "知乎热门讨论",
                "source": "知乎热榜",
                "sourceIcon": "💬",
                "url": "https://www.zhihu.com/hot",
                "category": "知识问答",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 知乎热榜: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 知乎热榜抓取异常: {e}")
    return articles


def fetch_toutiao():
    """抓取今日头条热点"""
    articles = []
    try:
        resp = safe_get("https://www.toutiao.com")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a[href*='/group/']")[:30]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not title or not href or len(title) < 5:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = f"https://www.toutiao.com{href}" if href.startswith("/") else href
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "今日头条热点资讯",
                "source": "今日头条",
                "sourceIcon": "📰",
                "url": url,
                "category": "热点资讯",
                "region": "国内",
                "importance": "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 今日头条: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 今日头条抓取异常: {e}")
    return articles


def fetch_baidu_hot():
    """抓取百度热搜"""
    articles = []
    try:
        resp = safe_get("https://top.baidu.com/board?tab=realtime")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".c-single-text-ellipsis")[:30]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            if not title or title in seen:
                continue
            seen.add(title)
            articles.append({
                "id": make_id(title, "https://top.baidu.com"),
                "title": title,
                "summary": "百度实时热搜",
                "source": "百度热搜",
                "sourceIcon": "🔍",
                "url": "https://top.baidu.com/board?tab=realtime",
                "category": "热点资讯",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 百度热搜: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 百度热搜抓取异常: {e}")
    return articles


def fetch_163_news():
    """抓取网易新闻热点"""
    articles = []
    try:
        resp = safe_get("https://news.163.com")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a.news_title")[:30]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not title or not href:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = href if href.startswith("http") else f"https://news.163.com{href}"
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "网易新闻热点",
                "source": "网易新闻",
                "sourceIcon": "📰",
                "url": url,
                "category": "热点资讯",
                "region": "国内",
                "importance": "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 网易新闻: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 网易新闻抓取异常: {e}")
    return articles


def fetch_sohu_news():
    """抓取搜狐新闻热点"""
    articles = []
    try:
        resp = safe_get("https://www.sohu.com")
        if not resp:
            return articles
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a[href*='/a/']")[:30]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not title or not href or len(title) < 10:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = href if href.startswith("http") else f"https://www.sohu.com{href}"
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "搜狐新闻热点",
                "source": "搜狐新闻",
                "sourceIcon": "📰",
                "url": url,
                "category": "热点资讯",
                "region": "国内",
                "importance": "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 搜狐新闻: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 搜狐新闻抓取异常: {e}")
    return articles

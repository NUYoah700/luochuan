#!/usr/bin/env python3
"""
洛川 - AI信息自动抓取引擎
每日从国内外多个来源采集AI相关资讯，输出JSON供前端展示
"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 修复Windows终端UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup

# ── DeepSeek API ──
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ── 配置 ──
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
}

# ── 工具函数 ──
def safe_get(url, params=None, headers=None):
    """安全HTTP请求，优先系统代理，失败时直连回退"""
    for use_proxy in (True, False):
        try:
            proxies = None if use_proxy else {"http": None, "https": None}
            resp = requests.get(
                url, params=params, headers=headers or HEADERS,
                timeout=REQUEST_TIMEOUT, proxies=proxies,
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            if use_proxy:
                continue  # 代理失败，尝试直连
            print(f"  ⚠ 请求失败: {url} → {e}")
            return None

def make_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_local_config():
    """加载本地配置文件"""
    cfg_file = Path(__file__).parent / "config.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

# ── 数据源：Hacker News (AI相关热门) ──
def fetch_hackernews():
    """从HN API获取AI相关热门文章"""
    articles = []
    try:
        # 获取热门文章ID
        resp = safe_get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not resp:
            return articles
        ids = resp.json()[:80]

        ai_keywords = [
            "ai", "llm", "gpt", "openai", "claude", "anthropic", "gemini",
            "model", "transformer", "deepseek", "llama", "mistral", "copilot",
            "agent", "diffusion", "stable", "midjourney", "sora", "cursor",
            "chatgpt", "machine learning", "deep learning", "neural", "token",
            "embedding", "rag", "fine-tune", "inference", "gpu", "nvidia"
        ]

        for item_id in ids[:60]:
            item_resp = safe_get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
            if not item_resp:
                continue
            item = item_resp.json()
            if not item or "title" not in item:
                continue

            title_lower = item["title"].lower()
            if any(kw in title_lower for kw in ai_keywords):
                url = item.get("url", f"https://news.ycombinator.com/item?id={item_id}")
                articles.append({
                    "id": make_id(item["title"], url),
                    "title": item["title"],
                    "summary": f"Score: {item.get('score', 0)} | Comments: {item.get('descendants', 0)}",
                    "source": "Hacker News",
                    "sourceIcon": "🔶",
                    "url": url,
                    "category": "技术动态",
                    "region": "国际",
                    "importance": "high" if item.get("score", 0) > 100 else "normal",
                    "timestamp": now_iso(),
                    "raw_date": datetime.fromtimestamp(item.get("time", 0)).strftime("%Y-%m-%d %H:%M"),
                })
        print(f"  ✓ Hacker News: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ Hacker News 抓取异常: {e}")
    return articles


# ── 数据源：Reddit r/artificial + r/MachineLearning ──
def fetch_reddit_ai():
    """从Reddit AI相关子版块获取热帖"""
    articles = []
    subreddits = ["artificial", "MachineLearning", "ChatGPT", "OpenAI", "LocalLLaMA"]
    for sub in subreddits:
        try:
            url = f"https://old.reddit.com/r/{sub}/hot.json?limit=15"
            resp = safe_get(url, headers={**HEADERS, "Accept": "application/json", "User-Agent": "python:luochuan:v1.0 (by /u/luochuan_bot)"})
            if not resp:
                continue
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                p = post["data"]
                if p.get("stickied"):
                    continue
                title = p.get("title", "")
                articles.append({
                    "id": make_id(title, f"https://reddit.com{p.get('permalink', '')}"),
                    "title": title,
                    "summary": f"r/{sub} | ↑{p.get('ups', 0)} | 💬{p.get('num_comments', 0)}",
                    "source": f"Reddit r/{sub}",
                    "sourceIcon": "🤖",
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "category": "社区热议",
                    "region": "国际",
                    "importance": "high" if p.get("ups", 0) > 500 else "normal",
                    "timestamp": now_iso(),
                    "raw_date": datetime.fromtimestamp(p.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception as e:
            print(f"  ⚠ Reddit r/{sub} 抓取异常: {e}")
    print(f"  ✓ Reddit AI: {len(articles)} 篇")
    return articles


# ── 数据源：GitHub Trending（所有热门项目） ──
def fetch_github_trending_ai():
    """获取GitHub今日热门仓库，不限领域"""
    articles = []
    try:
        url = "https://github.com/trending?since=daily&spoken_language_code="
        resp = safe_get(url)
        if not resp:
            return articles

        soup = BeautifulSoup(resp.text, "html.parser")
        repos = soup.select("article.Box-row")

        for repo in repos:
            h2 = repo.select_one("h2")
            if not h2:
                continue
            name = h2.get_text(strip=True)
            name = name.replace(" / ", "/").replace(" /", "/").replace("/ ", "/").strip()
            if not name or "/" not in name:
                continue
            if len(articles) >= 20:
                break
            desc_el = repo.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # 获取编程语言
            lang_el = repo.select_one("[itemprop='programmingLanguage']")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            # 获取 star 数
            stars_el = repo.select_one(".d-inline-block.float-sm-right")
            stars = ""
            if stars_el:
                stars_text = stars_el.get_text(strip=True)
                stars_match = re.search(r'[\d,]+', stars_text)
                if stars_match:
                    stars = stars_match.group()

            repo_url = f"https://github.com/{name.strip()}"
            extra = f"⭐ {stars}" if stars else ""
            if lang:
                extra = f"{extra} · {lang}" if extra else lang

            articles.append({
                "id": make_id(name, repo_url),
                "title": name.strip(),
                "summary": desc[:250] if desc else "查看项目详情",
                "lang": lang,
                "stars": stars,
                "source": "GitHub Trending",
                "sourceIcon": "⭐",
                "url": repo_url,
                "category": "开源项目",
                "region": "国际",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ GitHub Trending: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ GitHub 抓取异常: {e}")
    return articles


# ── 数据源：ArXiv AI 最新论文 ──
def fetch_arxiv_ai():
    """获取ArXiv最新AI论文"""
    articles = []
    try:
        # 使用ArXiv API查询cs.AI分类最新论文
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": "cat:cs.AI",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": "15",
        }
        resp = safe_get(url, params=params)
        if not resp:
            return articles

        soup = BeautifulSoup(resp.text, "xml")
        for entry in soup.find_all("entry")[:12]:
            title = entry.find("title").get_text(strip=True) if entry.find("title") else ""
            summary = entry.find("summary").get_text(strip=True)[:250] if entry.find("summary") else ""
            link = entry.find("id").get_text(strip=True) if entry.find("id") else ""
            published = entry.find("published").get_text(strip=True)[:10] if entry.find("published") else ""
            articles.append({
                "id": make_id(title, link),
                "title": title,
                "summary": summary,
                "source": "ArXiv cs.AI",
                "sourceIcon": "📄",
                "url": link,
                "category": "学术论文",
                "region": "国际",
                "importance": "normal",
                "timestamp": now_iso(),
                "raw_date": published,
            })
        print(f"  ✓ ArXiv: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ ArXiv 抓取异常: {e}")
    return articles


# ── 数据源：机器之心 (jiqizhixin.com) ──
def fetch_jiqizhixin():
    """抓取机器之心最新AI文章"""
    articles = []
    try:
        resp = safe_get("https://www.jiqizhixin.com/")
        if not resp:
            return articles
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a[href*='/articles/']")[:15]
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not title or not href or len(title) < 10:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = f"https://www.jiqizhixin.com{href}" if href.startswith("/") else href
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "机器之心AI前沿报道",
                "source": "机器之心",
                "sourceIcon": "🧠",
                "url": url,
                "category": "行业动态",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 机器之心: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 机器之心 抓取异常: {e}")
    return articles


# ── 数据源：量子位 (qbitai.com) ──
def fetch_qbitai():
    """抓取量子位最新文章"""
    articles = []
    try:
        resp = safe_get("https://www.qbitai.com/")
        if not resp:
            return articles
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("a[href*='/article/'], a[href*='/p/']")[:15]
        seen = set()
        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href or len(title) < 8:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = href if href.startswith("http") else f"https://www.qbitai.com{href}"
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "量子位AI科技报道",
                "source": "量子位",
                "sourceIcon": "⚛️",
                "url": url,
                "category": "行业动态",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 量子位: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 量子位 抓取异常: {e}")
    return articles


# ── 数据源：The Verge AI ──
def fetch_theverge_ai():
    """抓取The Verge AI板块"""
    articles = []
    try:
        resp = safe_get("https://www.theverge.com/ai-artificial-intelligence")
        if not resp:
            return articles
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("a[href*='/202']")[:15]  # 2026年文章
        seen = set()
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not title or not href or len(title) < 15:
                continue
            if title in seen:
                continue
            seen.add(title)
            url = f"https://www.theverge.com{href}" if href.startswith("/") else href
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": "The Verge AI板块报道",
                "source": "The Verge",
                "sourceIcon": "📰",
                "url": url,
                "category": "行业动态",
                "region": "国际",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ The Verge AI: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ The Verge 抓取异常: {e}")
    return articles


# ── 数据源：生活资讯 ──
def fetch_lifestyle():
    """抓取生活资讯"""
    articles = []
    try:
        sources = [
            ("Apartment Therapy", "https://www.apartmenttherapy.com", "🏠"),
            ("Lifehacker", "https://lifehacker.com", "💡"),
            ("Real Simple", "https://www.realsimple.com", "🌸"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".post-title a",
                    ".headline a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 10:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 生活资讯",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "生活资讯",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 15:
                            break
                    if len(articles) >= 15:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 生活资讯: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 生活资讯抓取异常: {e}")
    return articles


# ── 数据源：科技数码 ──
def fetch_tech_digital():
    """抓取科技数码资讯"""
    articles = []
    try:
        sources = [
            ("Engadget", "https://www.engadget.com", "📱"),
            ("The Verge Tech", "https://www.theverge.com/tech", "💻"),
            ("Gizmodo", "https://gizmodo.com", "🔧"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".post-title a",
                    ".headline a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 10:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 科技数码资讯",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "科技数码",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 15:
                            break
                    if len(articles) >= 15:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 科技数码: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 科技数码抓取异常: {e}")
    return articles


# ── 数据源：更多 Reddit 版块 ──
def fetch_reddit_more():
    """从更多 Reddit 子版块获取热帖"""
    articles = []
    subreddits = [
        ("news", "社区热议"),
        ("worldnews", "国际新闻"),
        ("technology", "科技数码"),
        ("gaming", "游戏资讯"),
        ("movies", "娱乐影视"),
        ("music", "音乐资讯"),
        ("sports", "体育资讯"),
        ("science", "科学探索"),
        ("askscience", "科学问答"),
        ("todayilearned", "知识科普"),
        ("funny", "趣味内容"),
        ("aww", "萌宠内容"),
    ]
    
    for sub, category in subreddits:
        try:
            url = f"https://old.reddit.com/r/{sub}/hot.json?limit=10"
            resp = safe_get(url, headers={**HEADERS, "Accept": "application/json", "User-Agent": "python:luochuan:v1.0 (by /u/luochuan_bot)"})
            if not resp:
                continue
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                p = post["data"]
                if p.get("stickied"):
                    continue
                title = p.get("title", "")
                articles.append({
                    "id": make_id(title, f"https://reddit.com{p.get('permalink', '')}"),
                    "title": title,
                    "summary": f"r/{sub} | ↑{p.get('ups', 0)} | 💬{p.get('num_comments', 0)}",
                    "source": f"Reddit r/{sub}",
                    "sourceIcon": "📌",
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "category": category,
                    "region": "国际",
                    "importance": "high" if p.get("ups", 0) > 1000 else "normal",
                    "timestamp": now_iso(),
                    "raw_date": datetime.fromtimestamp(p.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception as e:
            print(f"  ⚠ Reddit r/{sub} 抓取异常: {e}")
    
    print(f"  ✓ Reddit 更多版块: {len(articles)} 篇")
    return articles


# ── 数据源：国际新闻媒体 ──
def fetch_international_news():
    """抓取国际新闻媒体资讯"""
    articles = []
    try:
        sources = [
            ("BBC News", "https://www.bbc.com/news", "📰"),
            ("CNN", "https://www.cnn.com", "📺"),
            ("Reuters", "https://www.reuters.com", "📡"),
            ("Associated Press", "https://apnews.com", "📋"),
            ("The New York Times", "https://www.nytimes.com", "🗞️"),
            ("The Guardian", "https://www.theguardian.com", "📰"),
            ("Al Jazeera", "https://www.aljazeera.com", "🌍"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".headline a",
                    ".title a",
                    "h2 a",
                    "h3 a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 15:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:", "/help/", "/about/", "/contact/"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 国际新闻",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "国际新闻",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 30:
                            break
                    if len(articles) >= 30:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 国际新闻媒体: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 国际新闻媒体抓取异常: {e}")
    return articles


# ── 数据源：娱乐八卦 ──
def fetch_entertainment():
    """抓取娱乐八卦资讯"""
    articles = []
    try:
        sources = [
            ("TMZ", "https://www.tmz.com", "🎬"),
            ("Entertainment Weekly", "https://ew.com", "⭐"),
            ("Variety", "https://variety.com", "🎭"),
            ("Hollywood Reporter", "https://www.hollywoodreporter.com", "🎥"),
            ("People", "https://people.com", "👤"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".headline a",
                    ".title a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 10:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 娱乐资讯",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "娱乐八卦",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 20:
                            break
                    if len(articles) >= 20:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 娱乐八卦: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 娱乐八卦抓取异常: {e}")
    return articles


# ── 数据源：体育资讯 ──
def fetch_sports():
    """抓取体育资讯"""
    articles = []
    try:
        sources = [
            ("ESPN", "https://www.espn.com", "⚽"),
            ("Sports Illustrated", "https://www.si.com", "🏈"),
            ("Bleacher Report", "https://bleacherreport.com", "🏀"),
            ("Sky Sports", "https://www.skysports.com", "⚾"),
            ("BBC Sport", "https://www.bbc.com/sport", "🎾"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".headline a",
                    ".title a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 10:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 体育资讯",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "体育资讯",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 20:
                            break
                    if len(articles) >= 20:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 体育资讯: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 体育资讯抓取异常: {e}")
    return articles


# ── 数据源：财经新闻 ──
def fetch_finance():
    """抓取财经新闻"""
    articles = []
    try:
        sources = [
            ("Bloomberg", "https://www.bloomberg.com", "💰"),
            ("Financial Times", "https://www.ft.com", "📊"),
            ("CNBC", "https://www.cnbc.com", "📈"),
            ("MarketWatch", "https://www.marketwatch.com", "📉"),
            ("Yahoo Finance", "https://finance.yahoo.com", "💵"),
        ]
        seen = set()
        
        for name, url, icon in sources:
            try:
                resp = safe_get(url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                
                selectors = [
                    "a[href]",
                    "article a",
                    ".headline a",
                    ".title a",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)[:10]
                    for item in items:
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        if not title or not href or len(title) < 10:
                            continue
                        if title in seen:
                            continue
                        if any(x in href.lower() for x in ["/tag/", "/category/", "#", "javascript:"]):
                            continue
                        seen.add(title)
                        full_url = href if href.startswith("http") else (url.rstrip("/") + href if href.startswith("/") else url + "/" + href)
                        articles.append({
                            "id": make_id(title, full_url),
                            "title": title,
                            "summary": f"{name} 财经新闻",
                            "source": name,
                            "sourceIcon": icon,
                            "url": full_url,
                            "category": "财经新闻",
                            "region": "国际",
                            "importance": "normal",
                            "timestamp": now_iso(),
                            "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        if len(articles) >= 20:
                            break
                    if len(articles) >= 20:
                        break
            except Exception as e:
                print(f"  ⚠ {name} 抓取异常: {e}")
                continue
        
        print(f"  ✓ 财经新闻: {len(articles)} 篇")
    except Exception as e:
        print(f"  ⚠ 财经新闻抓取异常: {e}")
    return articles


# ── DeepSeek 中文总结 ──
def add_chinese_summaries(articles, config):
    """用 DeepSeek 给每篇文章生成中文简介和用途说明"""
    api_key = config.get("deepseek_key", "")
    if not api_key:
        print("  ⚠ 未配置 deepseek_key，跳过中文总结")
        return

    # 分批处理，每批 10 篇
    batch_size = 10
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        items_json = json.dumps([
            {
                "index": idx,
                "title": a["title"],
                "desc": a.get("summary", "")[:150],
                "source": a["source"],
                "lang": a.get("lang", ""),
                "stars": a.get("stars", ""),
            }
            for idx, a in enumerate(batch)
        ], ensure_ascii=False)

        prompt = f"""以下是今日热门 GitHub/GitHub Trending 项目和其他AI资讯。请为每条资讯写一句中文简介（不超过40字），说明这个项目的用途或这条资讯的价值。

返回一个JSON数组，每一项格式：{{"index": 序号, "summary_cn": "一句话中文简介"}}

资讯列表：
{items_json}"""

        try:
            resp = requests.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # 解析返回的 JSON
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                summaries = json.loads(json_match.group())
                for s in summaries:
                    idx = i + s["index"]
                    if idx < len(articles):
                        articles[idx]["summary_cn"] = s.get("summary_cn", "")
                print(f"  ✓ DeepSeek 总结: {len(summaries)} 条")
            else:
                print(f"  ⚠ DeepSeek 返回格式异常: {content[:100]}")

        except Exception as e:
            print(f"  ⚠ DeepSeek API 错误: {e}")
            continue

        if i + batch_size < len(articles):
            time.sleep(0.5)  # API 速率限制

# ── 主函数 ──
def collect_all():
    """采集所有数据源并合并去重"""
    print(f"\n{'='*60}")
    print(f"  洛川 AI 信息抓取引擎")
    print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    all_articles = []

    sources = [
        ("Hacker News", fetch_hackernews),
        ("Reddit AI", fetch_reddit_ai),
        ("GitHub Trending", fetch_github_trending_ai),
        ("ArXiv AI", fetch_arxiv_ai),
        ("机器之心", fetch_jiqizhixin),
        ("量子位", fetch_qbitai),
        ("The Verge AI", fetch_theverge_ai),
        ("生活资讯", fetch_lifestyle),
        ("科技数码", fetch_tech_digital),
        ("Reddit 更多", fetch_reddit_more),
        ("国际新闻", fetch_international_news),
        ("娱乐八卦", fetch_entertainment),
        ("体育资讯", fetch_sports),
        ("财经新闻", fetch_finance),
    ]

    for name, fetcher in sources:
        print(f"  📡 正在抓取 {name}...")
        try:
            articles = fetcher()
            all_articles.extend(articles)
        except Exception as e:
            print(f"  ❌ {name} 抓取失败: {e}")
        time.sleep(0.5)  # 礼貌延迟

    # 去重
    seen_ids = set()
    unique = []
    for article in all_articles:
        if article["id"] not in seen_ids:
            seen_ids.add(article["id"])
            unique.append(article)

    # 按重要性排序
    unique.sort(key=lambda x: (0 if x["importance"] == "high" else 1, x["title"]))

    # 加载配置获取 DeepSeek key
    config = load_local_config()

    # DeepSeek 中文总结
    print(f"\n  🤖 DeepSeek 生成中文简介...")
    add_chinese_summaries(unique, config)

    # 构建输出
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": now_iso(),
        "total": len(unique),
        "articles": unique,
    }

    # 保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ 采集完成: {len(unique)} 篇 (去重后)")
    print(f"  📁 保存至: {OUTPUT_FILE}\n")

    # 同时更新汇总索引
    update_index(unique)

    return output


def update_index(articles):
    """更新汇总索引文件，供前端加载多日数据"""
    index_file = DATA_DIR / "index.json"
    existing = []
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            pass

    today = datetime.now().strftime("%Y-%m-%d")
    dates_covered = {entry.get("date") for entry in existing}

    if today not in dates_covered:
        existing.append({
            "date": today,
            "count": len(articles),
            "file": f"{today}.json",
        })

    # 只保留最近30天
    existing = existing[-30:]
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def send_email_if_configured(output):
    """如果配置了邮箱，自动发送摘要"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from mailer import send_digest, load_config
        config = load_config()
        to_email = config.get("to_email", "")
        if to_email and output.get("articles"):
            print(f"\n  📧 发送邮件到 {to_email}...")
            send_digest(to_email, output["date"], output["articles"])
    except Exception as e:
        print(f"  ⚠ 邮件发送跳过: {e}")


if __name__ == "__main__":
    result = collect_all()
    send_email_if_configured(result)

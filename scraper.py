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


# ── 数据源：GitHub Trending AI/ML repos ──
def fetch_github_trending_ai():
    """获取GitHub今日热门AI仓库"""
    articles = []
    try:
        url = "https://github.com/trending?since=daily&spoken_language_code="
        resp = safe_get(url)
        if not resp:
            return articles

        # GitHub trending page parsing is unreliable via requests; use minimal approach
        # We grab the page and look for AI-related repos
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = soup.select("article.Box-row")[:25]

        ai_keywords = [
            "ai", "llm", "gpt", "openai", "claude", "deepseek", "llama",
            "agent", "diffusion", "transformer", "rag", "copilot", "cursor",
            "chatbot", "embedding", "inference"
        ]

        for repo in repos:
            h2 = repo.select_one("h2")
            if not h2:
                continue
            name = h2.get_text(strip=True)
            name = name.replace(" / ", "/").replace(" /", "/").replace("/ ", "/").strip()
            desc_el = repo.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            text = f"{name} {desc}".lower()
            if any(kw in text for kw in ai_keywords):
                repo_url = f"https://github.com/{name.strip()}"
                articles.append({
                    "id": make_id(name, repo_url),
                    "title": name.strip(),
                    "summary": desc[:200] if desc else "查看项目详情",
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
    index_file = DATA_DIR / "_index.json"
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

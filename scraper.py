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

# ── 图片相关 ──
def get_category_image(category):
    """根据分类返回Unsplash相关主题图片"""
    category_map = {
        "赚钱": "business",
        "创业": "startup",
        "投资": "finance",
        "ai": "artificial-intelligence",
        "科技": "technology",
        "技术": "technology",
        "职场": "business",
        "视频": "video-camera",
        "热门": "trending",
        "生活": "lifestyle",
        "商业": "business",
        "设计": "design",
        "艺术": "art",
        "论文": "science",
        "学术": "science",
        "开源": "code",
        "项目": "laptop-code",
    }
    
    keyword = "technology"
    for key, val in category_map.items():
        if key in category.lower():
            keyword = val
            break
    
    return f"https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&h=600&fit=crop"

def fetch_og_image(url):
    """从网页URL获取og:image或其他图片"""
    if not url or url == "#":
        return None
    
    try:
        resp = safe_get(url)
        if not resp:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 尝试 og:image
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img_url = og_img["content"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            return img_url
        
        # 尝试 twitter:image
        tw_img = soup.find("meta", name="twitter:image")
        if tw_img and tw_img.get("content"):
            img_url = tw_img["content"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            return img_url
        
        # 尝试 find a reasonable image
        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if src and (".jpg" in src or ".jpeg" in src or ".png" in src):
                if src.startswith("//"):
                    src = "https:" + src
                if src.startswith("/"):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                return src
    except:
        pass
    return None

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

# ── 图片填充函数 ──
def fill_images(articles):
    """为没有图片的文章填充相关图片"""
    # 预设的图片集合，按主题分
    default_images = [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800&h=600&fit=crop",
        "https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=800&h=600&fit=crop",
    ]
    
    for i, article in enumerate(articles):
        if not article.get("image"):
            # 优先用分类匹配
            category = article.get("category", "")
            title = article.get("title", "")
            source = article.get("source", "")
            
            # 循环用不同的图
            img_idx = i % len(default_images)
            article["image"] = default_images[img_idx]
            
            # 如果有特定来源，给特定图
            if "B站" in source or "视频" in category:
                article["image"] = "https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=800&h=600&fit=crop"
            elif "AI" in source or "AI" in title:
                article["image"] = "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop"
            elif "创业" in category or "投资" in category:
                article["image"] = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop"
            elif "职场" in category or "工作" in title:
                article["image"] = "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800&h=600&fit=crop"
            
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
        ("B站热门", fetch_bilibili),
        ("抖音热搜", fetch_douyin_hot),
        ("快手热搜", fetch_kuaishou_hot),
        ("36氪", fetch_36kr),
        ("虎嗅", fetch_huxiu),
        ("少数派", fetch_sspai),
        ("创业邦", fetch_cyzone),
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

    # 加载配置获取 DeepSeek key
    config = load_local_config()

    # DeepSeek 中文总结
    print(f"\n  🤖 DeepSeek 生成中文简介...")
    add_chinese_summaries(unique, config)
    
    # 填充图片
    print(f"\n  🖼️  正在为文章填充图片...")
    fill_images(unique)

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


# ── 数据源：B站热门视频 ──
def fetch_bilibili():
    """从B站API获取热门视频"""
    articles = []
    try:
        url = "https://api.bilibili.com/x/web-interface/ranking/v2"
        resp = safe_get(url, headers={**HEADERS, "Referer": "https://www.bilibili.com/"})
        if not resp:
            return articles
        
        data = resp.json()
        if data.get("code") != 0:
            return articles
        
        for item in data.get("data", {}).get("list", [])[:15]:
            title = item.get("title", "")
            desc = item.get("desc", "")[:150]
            bvid = item.get("bvid", "")
            url = f"https://www.bilibili.com/video/{bvid}"
            
            # 图片：B站API直接提供封面
            image = item.get("pic", "")
            if image and image.startswith("//"):
                image = "https:" + image
            
            stat = item.get("stat", {})
            plays = stat.get("view", 0)
            likes = stat.get("like", 0)
            
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": f"播放 {plays:,} | 点赞 {likes:,} | {desc[:80]}",
                "source": "B站",
                "sourceIcon": "📺",
                "url": url,
                "category": "热门视频",
                "region": "国内",
                "importance": "high" if plays > 1000000 else "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "image": image,
                "extra": {
                    "plays": plays,
                    "likes": likes,
                    "author": item.get("owner", {}).get("name", ""),
                    "duration": item.get("duration", 0)
                }
            })
        print(f"  ✓ B站热门: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ B站 抓取异常: {e}")
    return articles


# ── 数据源：抖音热搜 ──
def fetch_douyin_hot():
    """从抖音获取热搜榜单"""
    articles = []
    try:
        url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "keyword_request_num": "20"
        }
        resp = safe_get(url, params=params, headers={
            **HEADERS,
            "Referer": "https://www.douyin.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if not resp:
            print(f"  ⚠ 抖音热搜 抓取失败（可能需要代理）")
            return articles
        
        data = resp.json()
        word_list = data.get("data", {}).get("word_list", [])[:15]
        
        for item in word_list:
            word = item.get("word", "")
            hot_value = item.get("hot_value", 0)
            desc = item.get("sentence_desc", "")
            
            articles.append({
                "id": make_id(word, f"douyin_hot_{word}"),
                "title": f"🔥 {word}",
                "summary": f"抖音热搜 | 热度 {hot_value:,} | {desc}",
                "source": "抖音",
                "sourceIcon": "🎵",
                "url": f"https://www.douyin.com/search/{word}",
                "category": "热搜",
                "region": "国内",
                "importance": "high" if hot_value > 500000 else "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "extra": {"hot_value": hot_value}
            })
        print(f"  ✓ 抖音热搜: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 抖音热搜 抓取异常: {e}")
    return articles


# ── 数据源：快手热搜 ──
def fetch_kuaishou_hot():
    """从快手获取热搜榜单"""
    articles = []
    try:
        url = "https://www.kuaishou.com/graphql"
        payload = {
            "operationName": "hotSearch",
            "variables": {},
            "query": "query hotSearch { hotSearch { title heat }}"
        }
        
        resp = requests.post(
            url, 
            json=payload,
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        
        if not resp or resp.status_code != 200:
            print(f"  ⚠ 快手热搜 抓取失败（可能需要登录）")
            return articles
        
        data = resp.json()
        items = data.get("data", {}).get("hotSearch", [])[:15]
        
        for item in items:
            title = item.get("title", "")
            heat = item.get("heat", 0)
            
            articles.append({
                "id": make_id(title, f"kuaishou_hot_{title}"),
                "title": f"📱 {title}",
                "summary": f"快手热搜 | 热度 {heat:,}",
                "source": "快手",
                "sourceIcon": "🎬",
                "url": "https://www.kuaishou.com/search",
                "category": "热搜",
                "region": "国内",
                "importance": "high" if heat > 100000 else "normal",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "extra": {"heat": heat}
            })
        print(f"  ✓ 快手热搜: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 快手热搜 抓取异常: {e}")
    return articles


# ── 数据源：36氪 ──
def fetch_36kr():
    """抓取36氪最新文章"""
    articles = []
    try:
        url = "https://36kr.com/api/newsflash/index"
        params = {"per_page": 20, "page": 1}
        resp = safe_get(url, params=params, headers={**HEADERS, "Referer": "https://36kr.com/"})
        
        if not resp:
            return articles
        
        data = resp.json()
        items = data.get("data", {}).get("items", [])[:15]
        
        for item in items:
            title = item.get("title", "")
            if len(title) < 10:
                continue
            
            # 尝试获取图片
            image = item.get("cover", "") or item.get("image", "")
            if image and image.startswith("//"):
                image = "https:" + image
            
            articles.append({
                "id": make_id(title, str(item.get("id", ""))),
                "title": title,
                "summary": item.get("description", "")[:150] or "36氪深度报道",
                "source": "36氪",
                "sourceIcon": "💰",
                "url": item.get("route", "") or f"https://36kr.com/p/{item.get('id', '')}",
                "category": "创业投资",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": item.get("published_at", "")[:16] or datetime.now().strftime("%Y-%m-%d %H:%M"),
                "image": image,
            })
        print(f"  ✓ 36氪: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 36氪 抓取异常: {e}")
    return articles


# ── 数据源：虎嗅 ──
def fetch_huxiu():
    """抓取虎嗅最新文章"""
    articles = []
    try:
        url = "https://www.huxiu.com/v2/article/list.php"
        params = {"page": 1, "pageSize": 20}
        resp = safe_get(url, params=params, headers={**HEADERS, "Referer": "https://www.huxiu.com/"})
        
        if not resp:
            return articles
        
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".article-item")[:15]
        
        for item in items:
            title_el = item.select_one(".article-item__title")
            if not title_el:
                continue
            
            title = title_el.get_text(strip=True)
            href = item.select_one("a")
            url = href.get("href", "") if href else ""
            if not url.startswith("http"):
                url = f"https://www.huxiu.com{url}"
            
            meta_el = item.select_one(".article-item__info")
            meta = meta_el.get_text(strip=True) if meta_el else ""
            
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": meta[:150] or "虎嗅商业观察",
                "source": "虎嗅",
                "sourceIcon": "🐯",
                "url": url,
                "category": "商业观察",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 虎嗅: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 虎嗅 抓取异常: {e}")
    return articles


# ── 数据源：少数派 ──
def fetch_sspai():
    """抓取少数派最新文章"""
    articles = []
    try:
        url = "https://sspai.com/api/v1/article/tag/1000/page/1?limit=20"
        resp = safe_get(url, headers={**HEADERS, "Referer": "https://sspai.com/"})
        
        if not resp:
            return articles
        
        data = resp.json()
        items = data.get("data", [])[:15]
        
        for item in items:
            title = item.get("title", "")
            if len(title) < 10:
                continue
            
            article_id = item.get("id", "")
            url = f"https://sspai.com/post/{article_id}"
            
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": item.get("summary", "")[:150] or "少数派生活科技",
                "source": "少数派",
                "sourceIcon": "✌️",
                "url": url,
                "category": "科技生活",
                "region": "国内",
                "importance": "normal",
                "timestamp": now_iso(),
                "raw_date": item.get("created_at", "")[:16] or datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 少数派: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 少数派 抓取异常: {e}")
    return articles


# ── 数据源：创业邦 ──
def fetch_cyzone():
    """抓取创业邦最新文章"""
    articles = []
    try:
        url = "https://www.cyzone.cn/article/list/"
        resp = safe_get(url, headers={**HEADERS, "Referer": "https://www.cyzone.cn/"})
        
        if not resp:
            return articles
        
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".article-item")[:15]
        
        for item in items:
            title_el = item.select_one("h2 a") or item.select_one("h3 a")
            if not title_el:
                continue
            
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if not url.startswith("http"):
                url = f"https://www.cyzone.cn{url}"
            
            desc_el = item.select_one(".article-desc")
            desc = desc_el.get_text(strip=True)[:150] if desc_el else ""
            
            articles.append({
                "id": make_id(title, url),
                "title": title,
                "summary": desc or "创业邦深度报道",
                "source": "创业邦",
                "sourceIcon": "🚀",
                "url": url,
                "category": "创业投资",
                "region": "国内",
                "importance": "high",
                "timestamp": now_iso(),
                "raw_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        print(f"  ✓ 创业邦: {len(articles)} 条")
    except Exception as e:
        print(f"  ⚠ 创业邦 抓取异常: {e}")
    return articles


if __name__ == "__main__":
    result = collect_all()
    send_email_if_configured(result)

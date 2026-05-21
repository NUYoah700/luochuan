#!/usr/bin/env python3
"""
为已有的历史数据文件添加图片
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# 预设的图片集合
default_images = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=800&h=600&fit=crop",
]

def fill_images_for_articles(articles):
    """为文章列表填充图片"""
    for i, article in enumerate(articles):
        if not article.get("image"):
            category = article.get("category", "")
            title = article.get("title", "")
            source = article.get("source", "")
            
            img_idx = i % len(default_images)
            article["image"] = default_images[img_idx]
            
            if "B站" in source or "视频" in category:
                article["image"] = "https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=800&h=600&fit=crop"
            elif "AI" in source or "AI" in title:
                article["image"] = "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=600&fit=crop"
            elif "创业" in category or "投资" in category:
                article["image"] = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=600&fit=crop"
            elif "职场" in category or "工作" in title:
                article["image"] = "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800&h=600&fit=crop"
                
    return articles

def process_file(file_path):
    """处理单个数据文件"""
    print(f"正在处理: {file_path.name}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    if not articles:
        print("  没有文章，跳过")
        return
    
    count_before = sum(1 for a in articles if a.get("image"))
    print(f"  已有图片: {count_before}/{len(articles)}")
    
    fill_images_for_articles(articles)
    
    count_after = sum(1 for a in articles if a.get("image"))
    print(f"  处理后有图片: {count_after}/{len(articles)}")
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("  已保存")

def main():
    print("=" * 60)
    print("  洛川数据图片更新工具")
    print("=" * 60)
    
    if not DATA_DIR.exists():
        print(f"目录不存在: {DATA_DIR}")
        return
    
    json_files = sorted(DATA_DIR.glob("????-??-??.json"))
    
    print(f"找到 {len(json_files)} 个数据文件")
    print()
    
    for file_path in json_files:
        process_file(file_path)
        print()
    
    print("=" * 60)
    print("  完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()

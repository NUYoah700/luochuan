#!/usr/bin/env python3
"""
洛川 - 邮件发送模块
将每日AI资讯摘要发送到指定邮箱
"""

import json
import smtplib
import sys
import io
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── 配置 ──
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ── 邮件模板 ──
def build_html_digest(date_str, articles):
    """构建HTML格式的邮件摘要"""

    # 统计
    domestic = [a for a in articles if a["region"] == "国内"]
    intl = [a for a in articles if a["region"] in ("国际", "日本")]
    important = [a for a in articles if a["importance"] == "high"]

    cats = {}
    for a in articles:
        c = a["category"]
        cats[c] = cats.get(c, 0) + 1

    # 取重点文章前10
    highlights = sorted(articles, key=lambda a: (0 if a["importance"] == "high" else 1))[:10]

    cards_html = ""
    for a in highlights:
        importance_badge = '<span style="background:#4ade80;color:#000;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">🔥 重点</span>' if a["importance"] == "high" else ""
        cards_html += f"""
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.06);">
            <div style="font-size:14px;font-weight:600;color:#e8eaed;margin-bottom:6px;">
              {importance_badge}
              <a href="{a['url']}" style="color:#6c8cff;text-decoration:none;">{a['title']}</a>
            </div>
            <div style="font-size:12px;color:#9aa0b0;margin-bottom:4px;">
              {a.get('sourceIcon','')} {a['source']} · {a.get('raw_date','')} ·
              <span style="background:rgba(108,140,255,0.1);padding:1px 8px;border-radius:8px;font-size:10px">{a['region']}</span>
              <span style="color:#5a6070;margin-left:6px">{a['category']}</span>
            </div>
            ''' + (f'<div style="font-size:13px;color:#50e5c4;line-height:1.4;margin-bottom:4px;">💡 {a.get("summary_cn","")}</div>' if a.get('summary_cn') else '') + f'''
            <div style="font-size:13px;color:#5a6070;line-height:1.4;">{a.get('summary','')[:180]}</div>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0a0c14;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0c14;padding:30px 0;">
<tr><td align="center">

  <!-- 主容器 -->
  <table width="620" cellpadding="0" cellspacing="0" style="background:rgba(22,25,40,0.8);border-radius:14px;border:1px solid rgba(255,255,255,0.06);">

    <!-- Header -->
    <tr>
      <td style="padding:28px 30px 20px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="display:inline-block;width:44px;height:44px;background:linear-gradient(135deg,#6c8cff,#4f5fd0);border-radius:12px;line-height:44px;font-size:22px;color:#fff;font-weight:700;margin-bottom:10px;">洛</div>
        <h1 style="margin:0;font-size:22px;color:#e8eaed;letter-spacing:2px;">洛 川 · AI 每日资讯</h1>
        <p style="margin:6px 0 0;font-size:13px;color:#5a6070;">{date_str} · 共 {len(articles)} 篇资讯</p>
      </td>
    </tr>

    <!-- Stats -->
    <tr>
      <td style="padding:20px 30px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="text-align:center;padding:8px;background:rgba(255,255,255,0.03);border-radius:8px;">
              <div style="font-size:22px;font-weight:700;color:#e8eaed;">{len(articles)}</div>
              <div style="font-size:11px;color:#5a6070;">总资讯</div>
            </td>
            <td width="8"></td>
            <td style="text-align:center;padding:8px;background:rgba(255,255,255,0.03);border-radius:8px;">
              <div style="font-size:22px;font-weight:700;color:#6c8cff;">{len(important)}</div>
              <div style="font-size:11px;color:#5a6070;">重点</div>
            </td>
            <td width="8"></td>
            <td style="text-align:center;padding:8px;background:rgba(255,255,255,0.03);border-radius:8px;">
              <div style="font-size:22px;font-weight:700;color:#50e5c4;">{len(domestic)}</div>
              <div style="font-size:11px;color:#5a6070;">国内</div>
            </td>
            <td width="8"></td>
            <td style="text-align:center;padding:8px;background:rgba(255,255,255,0.03);border-radius:8px;">
              <div style="font-size:22px;font-weight:700;color:#f0b860;">{len(intl)}</div>
              <div style="font-size:11px;color:#5a6070;">国际</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- 分类标签 -->
    <tr>
      <td style="padding:0 30px 16px;">
        {''.join(f'<span style="display:inline-block;padding:3px 12px;margin:3px;border-radius:12px;font-size:11px;background:rgba(108,140,255,0.08);color:#6c8cff;border:1px solid rgba(108,140,255,0.15);">{c} ({n})</span>' for c, n in cats.items())}
      </td>
    </tr>

    <!-- 重点文章列表 -->
    <tr>
      <td style="padding:0 30px 8px;">
        <h3 style="margin:0;font-size:15px;color:#e8eaed;">📌 今日重点</h3>
      </td>
    </tr>
    <tr>
      <td style="padding:8px 10px 20px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(255,255,255,0.02);border-radius:12px;">
          {cards_html}
        </table>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding:20px 30px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#5a6070;">洛川 AI 资讯聚合 · 每日 06:00 自动推送</p>
        <p style="margin:0;font-size:11px;color:#3a4060;">
          查看完整内容请访问 <a href="#" style="color:#6c8cff;">洛川前端页面</a>
        </p>
      </td>
    </tr>

  </table>

</td></tr>
</table>
</body>
</html>"""
    return html


def send_digest(to_email, date_str, articles):
    """发送邮件摘要"""
    config = load_config()

    smtp_user = config.get("smtp_user") or config.get("gmail_user")
    smtp_pass = config.get("smtp_pass") or config.get("gmail_app_password")

    if not smtp_user or not smtp_pass:
        print("⚠ 未配置邮箱凭据，请先设置 config.json")
        print("  需要: gmail_user (你的Gmail地址)")
        print("  需要: gmail_app_password (Gmail应用专用密码)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(f"洛川 AI 每日资讯 · {date_str} · {len(articles)}篇", "utf-8")
    msg["From"] = Header(f"洛川 AI <{smtp_user}>", "utf-8")
    msg["To"] = to_email

    html_body = build_html_digest(date_str, articles)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"✓ 邮件已发送至 {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("⚠ Gmail 认证失败: 请检查应用专用密码是否正确")
        return False
    except Exception as e:
        print(f"⚠ 邮件发送失败: {e}")
        return False


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python mailer.py <收件邮箱> [日期]")
        print("示例: python mailer.py suxingchen37@gmail.com 2026-05-16")
        print()
        print("首次使用前请配置 config.json:")
        print('  {')
        print('    "gmail_user": "你的邮箱@gmail.com",')
        print('    "gmail_app_password": "16位应用专用密码"')
        print('  }')
        print()
        print("获取Gmail应用专用密码: https://myaccount.google.com/apppasswords")
        sys.exit(0)

    to = sys.argv[1]
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")

    data_file = Path(__file__).parent / "data" / f"{date_str}.json"
    if not data_file.exists():
        print(f"✗ 数据文件不存在: {data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    if not articles:
        print("没有文章可发送")
        sys.exit(0)

    print(f"准备发送 {date_str} 的 {len(articles)} 篇资讯到 {to}...")
    ok = send_digest(to, date_str, articles)
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""Push popular article to WeChat draft. Uses media/uploadimg for content images."""
import json, os, re, sys
from pathlib import Path

HOME = Path.home()
DRAFT = HOME / "writing-data/drafts/2026-05-09-科普-k线.md"
CHARTS_DIR = HOME / "writing-data/charts/2026-05-09"
WECHAT_APP_ID = "wx9776210069a7a9a0"

_env = HOME / ".hermes" / ".env"
if _env.exists():
    for _line in _env.read_text().split("\n"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, v = _line.split("=", 1)
            k, v = k.strip(), v.strip().strip("\"'")
            if k and v and k not in os.environ:
                os.environ[k] = v

import requests

def get_token():
    s = os.environ.get("WECHAT_APP_SECRET")
    if not s: print("E no WECHAT_APP_SECRET"); return None
    r = requests.get("https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type":"client_credential","appid":WECHAT_APP_ID,"secret":s}, timeout=15).json()
    if "access_token" in r: return r["access_token"]
    print(f"E token fail: {r}"); return None

def upload_content_img(token, path):
    """Upload image for inline article content. Uses media/uploadimg."""
    fname = Path(path).name
    with open(path, "rb") as f:
        r = requests.post("https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            params={"access_token": token},
            files={"media": (fname, f, "image/png")}, timeout=30).json()
    if "url" in r:
        print(f"  OK upload content: {fname}")
        return r["url"]
    print(f"  W upload content {fname}: {r}"); return None

def upload_cover(token, path):
    """Upload cover image. Uses material/add_material."""
    fname = Path(path).name
    with open(path, "rb") as f:
        r = requests.post("https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (fname, f, "image/png")}, timeout=30).json()
    if "media_id" in r:
        print(f"  OK upload cover: {fname}")
        return r["media_id"]
    print(f"  W upload cover {fname}: {r}"); return None

def create_draft(title, html, digest, token, thumb_id):
    art = {"title": title[:64], "author": "AI科普", "digest": digest[:120],
           "content": html, "need_open_comment": 1,
           "only_fans_can_comment": 0, "is_aigc": 1}
    if thumb_id: art["thumb_media_id"] = thumb_id
    r = requests.post("https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": token},
        data=json.dumps({"articles": [art]}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}, timeout=30).json()
    if "media_id" in r:
        print(f"OK draft created! media_id={r['media_id'][:20]}...")
        return True
    print(f"E draft fail: {r}"); return False

def convert(md, img_urls):
    """Convert markdown to WeChat HTML with embedded images."""
    parts = []
    for line in md.strip().split("\n"):
        s = line.strip()
        if not s:
            parts.append("<p><br/></p>")
        elif s == "---":
            parts.append("<hr/>")
        elif s.startswith("# "):
            t = s[2:]
            parts.append(f'<h2 style="font-size:20px;font-weight:bold;color:#222;margin:25px 0 12px 0;text-align:center;border-bottom:2px solid #ffb347;padding-bottom:8px;">{t}</h2>')
        elif s.startswith("## "):
            t = s[3:]
            parts.append(f'<h3 style="font-size:17px;font-weight:bold;color:#333;margin:20px 0 10px 0;border-left:4px solid #ffb347;padding-left:10px;">{t}</h3>')
        elif s.startswith("!["):
            m = re.search(r'!\[.*?\]\(charts/([^)]+)\)', s)
            if m and m.group(1) in img_urls:
                parts.append(f'<p style="text-align:center;margin:15px 0;"><img src="{img_urls[m.group(1)]}" style="width:100%;max-width:600px;display:block;margin:0 auto;"/></p>')
            else:
                parts.append("<p><br/></p>")
        elif s.startswith("**") and s.endswith("**"):
            parts.append(f'<p style="font-weight:bold;color:#333;margin:10px 0;">{s[2:-2]}</p>')
        else:
            parts.append(f'<p style="line-height:1.8;color:#444;margin:8px 0;font-size:15px;">{s}</p>')
    return "\n".join(parts)

md = DRAFT.read_text(encoding="utf-8")
title = "新手如何看K线？其实搞懂这3根就够了"
print(f"Push: {title}")

token = get_token()
if not token: sys.exit(1)

# Upload content images via media/uploadimg
img_urls = {}
for fname in ["kline_structure.png", "kline_red_green.png", "kline_trend.png"]:
    p = CHARTS_DIR / fname
    if p.exists():
        url = upload_content_img(token, str(p))
        if url: img_urls[fname] = url

# Upload cover via material/add_material
cover = CHARTS_DIR / "cover_popular.png"
thumb_id = None
if cover.exists():
    mid = upload_cover(token, str(cover))
    if mid: thumb_id = mid

html = convert(md, img_urls)
digest = "K线图就是股市的天气预报,搞懂红绿柱、上下影线,加上5日线和60日线,新手也能自己看走势了。"

print("Create draft...")
if create_draft(title, html, digest, token, thumb_id):
    print("OK 科普文章已同步到微信公众号草稿箱!")
    print("   请登录 https://mp.weixin.qq.com/ 审核后发布")

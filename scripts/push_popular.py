#!/usr/bin/env python3
"""Push popular science article to WeChat draft box."""
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
    print(f"E token: {r}"); return None

def upload_img(token, path):
    fname = Path(path).name
    with open(path, "rb") as f:
        r = requests.post("https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (fname, f, "image/png")}, timeout=30).json()
    if "media_id" in r: return r["media_id"], r.get("url", "")
    print(f"  W upload {fname}: {r}"); return None, None

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
        print(f"  OK draft! media_id={r['media_id'][:20]}...")
        return True
    print(f"  E draft fail: {r}"); return False

def md2html(md, img_urls):
    """Convert md to html, inject image CDN urls."""
    out = []
    for line in md.strip().split("\n"):
        s = line.strip()
        if not s:
            out.append("<p><br/></p>")
        elif s == "---":
            out.append("<hr/>")
        elif s.startswith("# "):
            out.append(f'<h2 style="font-size:20px;font-weight:bold;color:#222;margin:25px 0 12px 0;text-align:center;border-bottom:2px solid #ffb347;padding-bottom:8px;">{s[2:]}</h2>')
        elif s.startswith("## "):
            out.append(f'<h3 style="font-size:17px;font-weight:bold;color:#333;margin:20px 0 10px 0;border-left:4px solid #ffb347;padding-left:10px;">{s[3:]}</h3>')
        elif s.startswith("!["):
            m = re.search(r'!\[.*?\]\(charts/([^)]+)\)', s)
            if m and m.group(1) in img_urls:
                url = img_urls[m.group(1)]
                out.append(f'<p style="text-align:center;margin:15px 0;"><img src="{url}" style="max-width:100%;border-radius:8px;"/></p>')
            else:
                out.append("<p><br/></p>")
        elif s.startswith("* ") or s.startswith("- "):
            out.append(f'<li style="margin:3px 0;color:#444;line-height:1.6;">{s[2:]}</li>')
        elif s.startswith("**") and s.endswith("**"):
            out.append(f'<p style="font-weight:bold;color:#333;margin:10px 0;">{s[2:-2]}</p>')
        else:
            out.append(f'<p style="line-height:1.8;color:#444;margin:8px 0;font-size:15px;">{s}</p>')
    return "\n".join(out)

# Main
if not DRAFT.exists():
    print(f"E draft not found: {DRAFT}"); sys.exit(1)

md = DRAFT.read_text(encoding="utf-8")
title = "新手如何看K线？其实搞懂这3根就够了"
print(f"Push: {title}")

token = get_token()
if not token: sys.exit(1)
print("OK token")

# Upload images
img_urls = {}
for fname in ["kline_structure.png", "kline_red_green.png", "kline_trend.png"]:
    p = CHARTS_DIR / fname
    if p.exists():
        mid, url = upload_img(token, str(p))
        if mid:
            img_urls[fname] = url
            print(f"OK img: {fname}")

# Upload cover
cover = CHARTS_DIR / "cover_popular.png"
thumb_id = None
if cover.exists():
    mid, url = upload_img(token, str(cover))
    if mid: thumb_id = mid; print("OK cover")

# Build HTML
html = md2html(md, img_urls)
digest = "K线图就像股市的天气预报,搞懂红绿柱、上影线下影线,加上5日线和60日线,新手也能看懂走势。"

print("Create draft...")
if create_draft(title, html, digest, token, thumb_id):
    print("OK! 科普文章已同步到微信公众号草稿箱")
    print("   请登录 https://mp.weixin.qq.com/ 审核后发布")

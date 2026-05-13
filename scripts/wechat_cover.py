#!/usr/bin/env python3
"""微信公众号封面图上传 — 共享脚本，所有推送路径统一调用。
用法: python3 wechat_cover.py [--title TEXT]
输出: JSON {"thumb_media_id": "xxx", "url": "xxx"} 或 {"error": "xxx"}
"""

import os, sys, json, io, requests
from pathlib import Path

def get_access_token():
    """获取/刷新微信access_token"""
    appid = os.environ.get("WECHAT_APP_ID", "wx9776210069a7a9a0")
    env_secret = os.environ.get("WECHAT_APP_SECRET", "")
    # Shell env可能存旧格式(如146138.hpb)，.env优先
    secret = ""
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            line = line.strip()
            if line.startswith("WECHAT_APP_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")
    # .env为空时回退shell env
    if not secret and env_secret and len(env_secret) == 32:
        secret = env_secret
    
    if not secret:
        return None, "WECHAT_APP_SECRET not found in .env or env (need 32-char hex)"
    
    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": appid, "secret": secret},
        timeout=15
    )
    data = resp.json()
    if "access_token" in data:
        return data["access_token"], None
    return None, data.get("errmsg", str(data))


def generate_cover(title="A股财经"):
    """生成封面图PNG bytes"""
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (900, 500), color=(30, 60, 120))
    draw = ImageDraw.Draw(img)
    
    # 装饰线
    draw.rectangle([0, 0, 900, 8], fill=(255, 179, 71))
    draw.rectangle([0, 492, 900, 500], fill=(255, 179, 71))
    
    # 标题文字
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 48)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()
    
    # 居中绘制
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    x = (900 - tw) // 2
    draw.text((x, 200), title, fill=(255, 255, 255), font=font)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def upload_cover(token, image_bytes):
    """上传封面图到微信素材库"""
    resp = requests.post(
        "https://api.weixin.qq.com/cgi-bin/material/add_material",
        params={"access_token": token, "type": "image"},
        files={"media": ("cover.png", image_bytes, "image/png")},
        timeout=30
    )
    return resp.json()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="A股财经", help="封面标题")
    args = parser.parse_args()
    
    token, err = get_access_token()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)
    
    try:
        img_bytes = generate_cover(args.title)
        result = upload_cover(token, img_bytes)
        if "media_id" in result:
            print(json.dumps({
                "thumb_media_id": result["media_id"],
                "url": result.get("url", "")
            }))
        else:
            print(json.dumps({"error": str(result)}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

#!/usr/bin/env python3
"""Robust WeChat MP cookie extraction."""
import sys, json, time, re, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIE_FILE = Path.home() / ".hermes" / "credentials" / "wechat_cookies.json"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=str(Path.home() / ".hermes" / "browser-data" / "wechat-mp"),
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    page.goto("https://mp.weixin.qq.com/", timeout=30000)
    time.sleep(3)
    print(f"Current URL: {page.url}")
    
    login_urls = ["cgi-bin/home", "cgi-bin/indexpage", "cgi-bin/appmsg", "token="]
    logged_in = any(u in page.url for u in login_urls)
    
    if not logged_in:
        print("Not logged in. Waiting for manual login (QR scan)...")
        print("="*60)
        print("请用微信扫码登录")
        print("="*60)
        for i in range(150):
            time.sleep(2)
            url = page.url
            if any(u in url for u in login_urls):
                logged_in = True
                print(f"Login detected! URL: {url[:100]}")
                break
            if i % 30 == 0:
                print(f"  waiting... ({i*2}s)")
    
    if logged_in:
        cookies = browser.cookies()
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        txt_file = COOKIE_FILE.with_suffix('.txt')
        txt_file.write_text(cookie_str)
        
        print(f"Saved {len(cookies)} cookies to {COOKIE_FILE}")
        print(f"Domains: {set(c['domain'] for c in cookies)}")
        print(f"Names: {[c['name'] for c in cookies]}")
        
        # Test cookie by fetching CSRF token
        session = requests.Session()
        session.headers.update({
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        })
        editor_url = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&type=77&isNew=1&lang=zh_CN"
        r = session.get(editor_url, timeout=15)
        token_match = re.search(r'token=(\d+)', r.text)
        if token_match:
            print(f"CSRF token: {token_match.group(1)[:10]}... ✅ 可用")
        else:
            print("⚠️ No CSRF token found - cookies may be incomplete")
    else:
        print("Login timeout")
    
    browser.close()

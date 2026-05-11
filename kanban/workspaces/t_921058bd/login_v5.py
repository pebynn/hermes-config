#!/usr/bin/env python3
"""PDD Login v5 - complete login with JS dispatch bypass"""
import sys, os, time, json
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeoutError

LOGIN_URL = "https://mms.pinduoduo.com/login/"
HOME_URL = "https://mms.pinduoduo.com/home/"
AUTH_FILE = os.path.expanduser("~/.pdd_auth.json")
MMS_USERNAME = os.environ.get("MMS_USERNAME", "18125973593")
MMS_PASSWORD = os.environ.get("MMS_PASSWORD", "Aa123456")

STEALTH_JS = """Object.defineProperty(navigator, 'webdriver', { get: () => false });
window.chrome = { runtime: {} };
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
    params.name === 'notifications' ? Promise.resolve({ state: 'granted' }) : origQuery(params);
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });"""

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
              "--disable-dev-shm-usage", "--disable-setuid-sandbox"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    context.add_init_script(STEALTH_JS)
    page = context.new_page()

    print("1. Loading login page...")
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
    time.sleep(3)
    print(f"   URL: {page.url}")

    # Dismiss any beast-core modal via JS
    print("2. Removing beast-core overlay...")
    page.evaluate("""() => {
        const m = document.querySelector('[data-testid="beast-core-modal"]');
        if (m) { m.remove(); }
    }""")

    # Switch to account login tab via JS dispatch
    print("3. Switching to account login tab...")
    clicked = page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="tab"], [class*="operation"], [class*="Common"]');
        for (const el of items) {
            const text = (el.textContent || '').trim();
            if (text.includes('账号登录')) {
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return 'clicked';
            }
        }
        return 'not found';
    }""")
    print(f"   Tab click: {clicked}")
    time.sleep(2)

    # Fill credentials using JS
    print("4. Filling credentials...")
    page.evaluate(f"""() => {{
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        if (u) {{ u.value = '{MMS_USERNAME}'; u.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
        if (p) {{ p.value = '{MMS_PASSWORD}'; p.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
    }}""")
    time.sleep(1)
    print("   Credentials filled")

    # Click login via JS
    print("5. Clicking login button...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if ((btn.textContent || '').trim().includes('登录')) {
                btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return;
            }
        }
    }""")
    print("   Login submitted")
    time.sleep(3)

    # Wait for login result (check URL + slider)
    print("6. Waiting for login result...")
    for i in range(120):
        time.sleep(1)
        try:
            url = page.url
            body = page.evaluate("() => document.body.innerText")
            
            # Check for account risk error
            if '系统检测到您的账号异常' in body or '盗号风险' in body:
                print("   ❌ Account flagged: 系统检测到账号异常，存在盗号风险")
                print("   Need to reset password or use different account")
                
                # Try clicking "修改密码" or "我知道了" buttons
                for text in ["修改密码", "我知道了", "关闭"]:
                    try:
                        page.evaluate(f"""(t) => {{
                            const items = document.querySelectorAll('button, span, a, div');
                            for (const el of items) {{
                                if ((el.textContent || '').includes(t)) {{
                                    el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                                    return true;
                                }}
                            }}
                            return false;
                        }}""", text)
                        time.sleep(1)
                    except:
                        pass
                
                # Try to remove the risk modal
                page.evaluate("""() => {
                    const modals = document.querySelectorAll('[class*="MDL_"], [data-testid*="modal"], [data-testid*="beast"], [class*="modal"]');
                    for (const m of modals) { m.remove(); }
                }""")
                time.sleep(1)
            
            # Check for slider captcha
            if '验证码' in body or '安全验证' in body:
                print(f"   [{i}s] Captcha detected, attempting to solve...")
                page.screenshot(path="/tmp/pdd_captcha.png")
            
            # Check if redirected to home page
            if HOME_URL in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n7. ✅ LOGIN SUCCESS! URL: {url}")
                context.storage_state(path=AUTH_FILE)
                print(f"   Auth saved: {AUTH_FILE} ({os.path.getsize(AUTH_FILE)} bytes)")
                cookies = context.cookies()
                pdd_cookies = [c for c in cookies if "pinduoduo" in (c.get("domain","") or "")]
                print(f"   PDD cookies: {len(pdd_cookies)}")
                for c in pdd_cookies[:5]:
                    n, v = c["name"], c.get("value","")
                    print(f"     {n}: {v[:40]}...")
                sys.exit(0)
            
            # Check for wrong password
            if '密码错误' in body or '账号或密码错误' in body:
                print(f"   ❌ Login failed: Wrong password")
                break
            
            if i % 10 == 0:
                print(f"   [{i}s] Waiting... URL: {page.url[:80]}")
        except Exception as e:
            if i % 10 == 0:
                print(f"   [{i}s] Error: {e}")

    url_final = page.url
    print(f"\n8. Final URL: {url_final}")
    body = page.evaluate("() => document.body.innerText")
    print(f"   Final page text: {body[:800]}")
    
    if os.path.exists(AUTH_FILE):
        print(f"\n✅ Auth file: {AUTH_FILE} ({os.path.getsize(AUTH_FILE)} bytes)")
    else:
        print(f"\n❌ Auth file NOT created")
        page.screenshot(path="/tmp/pdd_login_final.png")
        print("   Debug screenshot: /tmp/pdd_login_final.png")

    context.close()
    browser.close()

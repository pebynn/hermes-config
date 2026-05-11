#!/usr/bin/env python3
"""PDD Login v6 - use Playwright native fill() after JS tab switch"""
import sys, os, time, json
from playwright.sync_api import sync_playwright

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

    # Remove beast-core overlay
    print("2. Removing beast-core overlay...")
    page.evaluate("""() => {
        const m = document.querySelector('[data-testid="beast-core-modal"]');
        if (m) { m.remove(); }
    }""")
    time.sleep(1)

    # Switch to account login tab
    print("3. Switching to account login tab...")
    page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="tab"], [class*="operation"], [class*="Common"]');
        for (const el of items) {
            const text = (el.textContent || '').trim();
            if (text.includes('账号登录')) {
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return;
            }
        }
    }""")
    time.sleep(2)

    # Use Playwright native fill() which properly triggers React events
    print("4. Filling username...")
    username_input = page.locator("#usernameId")
    username_input.fill(MMS_USERNAME, timeout=10000)
    print("   Username filled")
    time.sleep(1)

    print("5. Filling password...")
    password_input = page.locator("#passwordId")
    password_input.fill(MMS_PASSWORD, timeout=10000)
    print("   Password filled")
    time.sleep(1)

    # Click login
    print("6. Clicking login button...")
    login_btn = page.locator("button:has-text('登录')")
    if login_btn.count() > 0:
        login_btn.click(timeout=10000)
        print("   Login clicked via Playwright")
    else:
        # Fallback: JS click
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if ((btn.textContent || '').trim().includes('登录')) {
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    return;
                }
            }
        }""")
        print("   Login clicked via JS")

    time.sleep(3)

    # Wait for login result
    print("7. Waiting for login result...")
    for i in range(120):
        time.sleep(1)
        try:
            url = page.url
            body = page.evaluate("() => document.body.innerText")
            
            # Check for account risk
            if '系统检测到您的账号异常' in body:
                # Try to remove the risk modal
                page.evaluate("""() => {
                    const modals = document.querySelectorAll('[class*="MDL_"], [data-testid*="modal"]');
                    for (const m of modals) {
                        m.style.display = 'none';
                        m.remove();
                    }
                }""")
                time.sleep(1)
                url = page.url
                body = page.evaluate("() => document.body.innerText")
            
            # Success check
            if HOME_URL in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n✅ LOGIN SUCCESS! URL: {url}")
                context.storage_state(path=AUTH_FILE)
                print(f"   Auth saved: {AUTH_FILE} ({os.path.getsize(AUTH_FILE)} bytes)")
                sys.exit(0)

            if i % 10 == 0:
                print(f"   [{i}s] URL: {page.url[:80]}")
                if '请输入账号' in body or '请输入密码' in body:
                    print(f"   Form validation: {body[body.find('请输入账号'):body.find('请输入账号')+50]}")
        except:
            pass

    print(f"\n❌ Login timeout. URL: {page.url}")
    body = page.evaluate("() => document.body.innerText")
    print(f"   Page text: {body[:500]}")
    page.screenshot(path="/tmp/pdd_login_timeout.png")

    context.close()
    browser.close()

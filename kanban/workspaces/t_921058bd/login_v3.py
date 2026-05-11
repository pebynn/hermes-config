#!/usr/bin/env python3
"""PDD Login v3 - bypass beast-core modal, then login"""
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

def dismiss_beast_core(page):
    """Dismiss the beast-core browser warning modal via JS"""
    try:
        # JS to find and click close button of beast-core modal
        page.evaluate("""() => {
            // Find the beast-core modal
            const modal = document.querySelector('[data-testid="beast-core-modal"], [class*="MDL_outerWrapper"]');
            if (modal) {
                // Find close button
                const closeBtn = modal.querySelector('[class*="close"], button, [class*="MDL_icon"]');
                if (closeBtn) {
                    closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                }
                // Also try the "继续使用" or "我知道了" text
                const buttons = modal.querySelectorAll('button, span, div[role="button"]');
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim();
                    if (text.includes('继续') || text.includes('知道了') || text.includes('确定')) {
                        btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        break;
                    }
                }
                // Hide the modal by removing it
                modal.remove();
            }
        }""")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"  Dismiss beast-core error: {e}")
        return False

def click_via_js(page, selector_text):
    """Click an element via JS dispatchEvent to bypass overlay interception"""
    page.evaluate(f"""(text) => {{
        const items = document.querySelectorAll('a, button, span, div, li');
        for (const el of items) {{
            if ((el.textContent || '').trim().includes(text)) {{
                el.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                return el.textContent;
            }}
        }}
        return null;
    }}""", selector_text)

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

    print("1. Opening login page...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    print(f"   URL: {page.url}")

    print("2. Dismissing beast-core modal...")
    dismiss_beast_core(page)
    time.sleep(1)

    print("3. Switching to account login tab via JS...")
    clicked = page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="login"], [class*="tab"], li, span, div');
        for (const el of items) {
            const text = (el.textContent || '').trim();
            if (text.includes('账号登录') || text.includes('密码登录')) {
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return text;
            }
        }
        return null;
    }""")
    print(f"   Clicked: {clicked}")
    time.sleep(2)

    print("4. Filling credentials...")
    page.fill("input[type='text'], #usernameId, input[placeholder*='账号']", MMS_USERNAME)
    time.sleep(0.5)
    page.fill("input[type='password'], input[placeholder*='密码']", MMS_PASSWORD)
    time.sleep(0.5)

    print("5. Clicking login button via JS...")
    page.evaluate("""() => {
        const items = document.querySelectorAll('button');
        for (const btn of items) {
            const text = (btn.textContent || '').trim();
            if (text.includes('登录')) {
                btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return;
            }
        }
    }""")
    print("   Login submitted, waiting...")
    time.sleep(2)

    # Check for slider captcha
    print("6. Checking for slider captcha...")
    page.screenshot(path="/tmp/pdd_login_after.png")

    url_now = page.url
    body_text = page.evaluate("() => document.body.innerText")
    print(f"   URL: {url_now}")
    print(f"   Text preview: {body_text[:500]}")

    # Wait for login result
    for i in range(60):
        time.sleep(1)
        try:
            url = page.url
            if HOME_URL in url or "/home/" in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n7. LOGIN SUCCESS! URL: {url}")
                # Save auth state
                context.storage_state(path=AUTH_FILE)
                print(f"   Auth saved to {AUTH_FILE}")
                print(f"   Cookies: {len(context.cookies())}")
                break
        except:
            pass

        # Check body text for errors
        if i % 5 == 0:
            body = page.evaluate("() => document.body.innerText")
            for err_key in ["密码错误", "账号不存在", "验证码错误", "过于频繁", "安全风险"]:
                if err_key in body:
                    print(f"\n   ⚠️ Login error: '{err_key}' detected!")
                    break
    
    url_final = page.url
    print(f"\n8. Final URL: {url_final}")
    print(f"   Home URL in url: {HOME_URL in url_final}")

    # Check auth file
    if os.path.exists(AUTH_FILE):
        print(f"\n✅ Auth file created: {AUTH_FILE} ({os.path.getsize(AUTH_FILE)} bytes)")
    else:
        print(f"\n❌ Auth file NOT created")
        # Take a screenshot for debugging
        page.screenshot(path="/tmp/pdd_login_failed.png")
        print("   Screenshot saved: /tmp/pdd_login_failed.png")

    context.close()
    browser.close()

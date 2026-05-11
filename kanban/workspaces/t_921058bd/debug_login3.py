#!/usr/bin/env python3
"""PDD Login v4 - inspect page structure and login"""
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

    print("1. Loading page...")
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
    time.sleep(4)

    # Inspect the page structure around login tabs
    print("2. Inspecting page structure...")
    structure = page.evaluate("""() => {
        // Find the login form container
        const forms = document.querySelectorAll('[class*="login"], [class*="Login"], form, [class*="form"]');
        const result = [];
        for (const f of forms) {
            if (!f.offsetParent && !f.querySelector) continue;
            const rect = f.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 50) {
                result.push({
                    tag: f.tagName,
                    class: (f.className || '').slice(0,80),
                    rect: rect,
                    visible: f.offsetParent !== null,
                    html: f.innerHTML.slice(0, 500).replace(/</g, '&lt;')
                });
            }
        }
        return result;
    }""")

    for s in structure[:5]:
        print(f"\n  Form: tag={s['tag']} class={s['class']}")
        print(f"  Rect: {s['rect']['x']:.0f},{s['rect']['y']:.0f} {s['rect']['width']:.0f}x{s['rect']['height']:.0f}")
        print(f"  Visible: {s['visible']}")
        if s['visible']:
            print(f"  HTML: {s['html'][:300]}")
    
    # Find the login tabs and which one is active
    print("\n3. Looking for login tabs...")
    tabs = page.evaluate("""() => {
        const items = [];
        // Search through the DOM for tab-like elements
        const all = document.querySelectorAll('[class*="tab"], [class*="Tab"], [class*="header"], [class*="switch"], li');
        for (const el of all) {
            const text = (el.textContent || '').trim();
            if (text && (text.includes('扫码') || text.includes('账号') || text.includes('密码'))) {
                items.push({
                    tag: el.tagName,
                    text: text.slice(0,40),
                    class: (el.className || '').slice(0,60),
                    rect: el.getBoundingClientRect(),
                    visible: el.offsetParent !== null
                });
            }
        }
        return items;
    }""")
    
    for t in tabs:
        v = "VISIBLE" if t['visible'] else "hidden"
        print(f"  [{v}] tag={t['tag']} class={t['class']} text='{t['text']}'")
    
    # Use JS to directly activate the account login form
    print("\n4. Activating account login via JS...")
    activated = page.evaluate("""() => {
        // Method 1: Find all clickable elements with login-related text
        const clickables = document.querySelectorAll('a, button, span, div, li, label');
        for (const el of clickables) {
            const text = (el.textContent || '').trim();
            if (text === '账号登录') {
                console.log('Found 账号登录:', el);
                // Try removing any beast-core overlay first
                const modal = document.querySelector('[data-testid="beast-core-modal"]');
                if (modal) modal.style.display = 'none';
                
                // JS click
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                return 'clicked 账号登录 via dispatchEvent';
            }
        }
        
        // Method 2: Try programmatic activation
        const forms = document.querySelectorAll('[class*="login"]');
        for (const form of forms) {
            const inputs = form.querySelectorAll('input');
            if (inputs.length >= 2) {
                // This might be the account login form - make it visible
                form.style.display = 'block';
                form.style.visibility = 'visible';
                form.style.opacity = '1';
                return 'made password form visible';
            }
        }
        return 'no matching element found';
    }""")
    print(f"   Result: {activated}")
    time.sleep(2)
    
    # Check if the account form is now visible
    print("\n5. Checking inputs...")
    inputs = page.evaluate("""() => {
        const all = document.querySelectorAll('input');
        return Array.from(all).map(i => ({
            type: i.type,
            placeholder: i.placeholder,
            id: i.id,
            visible: i.offsetParent !== null,
            rect: i.getBoundingClientRect()
        }));
    }""")
    for inp in inputs:
        v = "VIS" if inp['visible'] else "hid"
        print(f"  [{v}] type={inp['type']:10s} placeholder='{inp['placeholder']}' id={inp['id']}")

    context.close()
    browser.close()

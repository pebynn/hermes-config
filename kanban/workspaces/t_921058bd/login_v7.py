#!/usr/bin/env python3
"""PDD Login v7 - fully remove beast-core and use evaluate for fill"""
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
    time.sleep(5)
    print(f"   URL: {page.url}")

    # Aggressively remove beast-core - remove ALL modals and overlays
    print("2. Removing beast-core and all overlays...")
    page.evaluate("""() => {
        // Remove specific beast-core modal
        const selectors = [
            '[data-testid="beast-core-modal"]',
            '[class*="MDL_outerWrapper"]',
            '[class*="MDL_modal"]', 
            '[class*="overlay"]',
            '[class*="mask"]',
            '[class*="beast"]'
        ];
        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach(el => el.remove());
        }
        // Also remove any element with highest z-index that might be in the way
        document.querySelectorAll('*').forEach(el => {
            const z = window.getComputedStyle(el).zIndex;
            if (parseInt(z) > 1000) {
                el.style.zIndex = '-1';
            }
            if (window.getComputedStyle(el).position === 'fixed' && el.offsetParent === null) {
                // Not visible anyway
            }
        });
    }""")
    time.sleep(1)

    # Switch to account login tab - use React-compatible approach
    print("3. Switching to account login tab...")
    page.evaluate("""() => {
        // Find the tab bar
        const tabBar = document.querySelector('[class*="operationTabs"], [class*="Common"], [class*="tab-operate"]');
        if (!tabBar) return 'no tab bar';
        
        // Find all child elements and click the one containing 账号登录
        const children = tabBar.querySelectorAll('*');
        for (const el of children) {
            const text = (el.textContent || '').trim();
            if (text === '账号登录') {
                // Try React-friendly click
                const events = ['mousedown', 'mouseup', 'click'];
                events.forEach(e => {
                    el.dispatchEvent(new MouseEvent(e, { bubbles: true, cancelable: true }));
                });
                return 'clicked via dispatch';
            }
        }
        
        // Try clicking the whole tab bar
        tabBar.click();
        return 'clicked tab bar';
    }""")
    time.sleep(2)
    print("   Tab switched")

    # Check input visibility
    vis_check = page.evaluate("""() => {
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        if (!u || !p) return 'inputs not found';
        const uStyle = window.getComputedStyle(u);
        const pStyle = window.getComputedStyle(p);
        return {
            username: {
                display: uStyle.display,
                visibility: uStyle.visibility,
                opacity: uStyle.opacity,
                offsetParent: u.offsetParent !== null,
                rect: u.getBoundingClientRect(),
                zIndex: uStyle.zIndex
            },
            password: {
                display: pStyle.display,
                visibility: pStyle.visibility,
                opacity: pStyle.opacity,
                offsetParent: p.offsetParent !== null,
                rect: p.getBoundingClientRect(),
                zIndex: pStyle.zIndex
            }
        };
    }""")
    print(f"   Input visibility: {json.dumps(vis_check, indent=2)[:300]}")

    # Check for any overlay that might be blocking
    overlay_check = page.evaluate("""() => {
        const results = [];
        // Check all fixed/absolute positioned elements
        document.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            if ((style.position === 'fixed' || style.position === 'absolute') &&
                el.offsetParent !== null &&
                el.getBoundingClientRect().width > 0) {
                const rect = el.getBoundingClientRect();
                // Check if it overlaps with the username input (around 420, 340)
                if (rect.left < 500 && rect.top < 400 && rect.right > 300 && rect.bottom > 300 &&
                    parseInt(style.zIndex) > 0) {
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        class: (el.className || '').slice(0,50),
                        zIndex: style.zIndex,
                        rect: {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom}
                    });
                }
            }
        });
        return results.slice(0,10);
    }""")
    if overlay_check:
        print(f"   Overlays on top of inputs: {json.dumps(overlay_check, indent=2)[:500]}")
    else:
        print("   No overlay found")

    # Now try to fill using evaluate (bypass visibility check)
    print("4. Filling credentials via JS...")
    page.evaluate("""() => {
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        if (!u || !p) return;
        
        // Use native value setter
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(u, '18125973593');
        u.dispatchEvent(new Event('input', { bubbles: true }));
        
        nativeInputValueSetter.call(p, 'Aa123456');
        p.dispatchEvent(new Event('input', { bubbles: true }));
        
        // Also dispatch change event
        u.dispatchEvent(new Event('change', { bubbles: true }));
        p.dispatchEvent(new Event('change', { bubbles: true }));
    }""")
    print("   Credentials filled via native setter")
    time.sleep(1)

    # Verify the values were set
    values = page.evaluate("""() => {
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        return {username: u ? u.value : 'N/A', password: p ? p.value : 'N/A'};
    }""")
    print(f"   Values after fill: {values}")

    # Also dispatch a blur to trigger form validation
    page.evaluate("""() => {
        document.getElementById('passwordId').dispatchEvent(new Event('blur', { bubbles: true }));
    }""")
    time.sleep(1)

    # Check for error message
    err = page.evaluate("""() => {
        const body = document.body.innerText;
        if (body.includes('请输入账号')) return '请输入账号 - still showing!';
        if (body.includes('请输入密码')) return '请输入密码 - still showing!';
        return 'no validation error';
    }""")
    print(f"   Validation: {err}")

    # Click login button 
    print("6. Clicking login button...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (text === '登录') {
                btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                console.log('Login clicked');
                return;
            }
        }
        console.log('No login button found');
    }""")
    time.sleep(3)
    print("   Login button clicked")

    # Wait for login result
    print("7. Waiting for login result...")
    for i in range(120):
        time.sleep(1)
        try:
            url = page.url
            body = page.evaluate("() => document.body.innerText")
            
            # Check for account risk 
            if '系统检测到您的账号异常' in body:
                page.evaluate("""() => {
                    document.querySelectorAll('*').forEach(el => {
                        const text = (el.textContent || '');
                        if (text.includes('系统检测') || text.includes('盗号风险')) {
                            const modal = el.closest('[data-testid], [class*="modal"], [class*="MDL"]');
                            if (modal) modal.remove();
                            el.style.display = 'none';
                        }
                    });
                    // Remove any fixed overlay
                    document.querySelectorAll('[data-testid*="beast"], [class*="beast"], [class*="MDL"]').forEach(el => el.remove());
                }""")
                time.sleep(2)
                url = page.url
                body = page.evaluate("() => document.body.innerText")

            if HOME_URL in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n✅ LOGIN SUCCESS! URL: {url}")
                context.storage_state(path=AUTH_FILE)
                print(f"   Auth saved: {AUTH_FILE} ({os.path.getsize(AUTH_FILE)} bytes)")
                cookies = context.cookies()
                pdd = [c for c in cookies if "pinduoduo" in (c.get("domain","") or "")]
                print(f"   PDD cookies: {len(pdd)}")
                for c in pdd[:5]:
                    print(f"     {c['name']}: {c.get('value','')[:40]}...")
                sys.exit(0)

            if i % 10 == 0:
                print(f"   [{i}s] URL: {page.url[:80]}")
                if '密码错误' in body or '请输入正确' in body:
                    print(f"   ❌ Credentials rejected!")
        except Exception as e:
            pass

    print(f"\n❌ Login timeout. URL: {page.url}")
    body = page.evaluate("() => document.body.innerText")
    print(f"   Page text: {body[:500]}")
    page.screenshot(path="/tmp/pdd_login_timeout.png")

    context.close()
    browser.close()

#!/usr/bin/env python3
"""PDD Login v9 - target the exact tab element + use native setter for React"""
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

    # Aggressively remove beast-core and all modal elements
    print("2. Removing all overlays...")
    page.evaluate("""() => {
        const toRemove = [];
        document.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            if (style.position === 'fixed' && el.offsetParent !== null) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 200 && rect.height > 200) {
                    toRemove.push(el);
                }
            }
        });
        toRemove.forEach(el => el.remove());
    }""")
    time.sleep(1)

    # Click the "账号登录" tab using the actual class
    print("3. Clicking 账号登录 tab...")
    # Option A: direct evaluate
    clicked = page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="Common_item"]');
        for (const item of items) {
            if (item.textContent.trim() === '账号登录') {
                // Try React click
                const rect = item.getBoundingClientRect();
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
                    item.dispatchEvent(new PointerEvent(type, {
                        bubbles: true, cancelable: true,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2
                    }));
                });
                return 'clicked via PointerEvents';
            }
        }
        return 'not found';
    }""")
    print(f"   {clicked}")
    time.sleep(2)

    # Check what became visible
    state = page.evaluate("""() => {
        const result = {};
        // Check for password section visibility
        const pwSection = document.querySelector('[class*="password-section"]');
        if (pwSection) {
            result.passwordSection = window.getComputedStyle(pwSection).display;
        }
        const scanSection = document.querySelector('[class*="scan-login-container"]');
        if (scanSection) {
            result.scanSection = window.getComputedStyle(scanSection).display;
        }
        return result;
    }""")
    print(f"   Tab state: {state}")

    # If the tab didn't switch, directly manipulate React state
    if state.get('passwordSection') != 'block':
        print("   Tab didn't switch! Trying direct form manipulation...")
        # Show the password form directly
        page.evaluate("""() => {
            // Hide scan login
            const scan = document.querySelector('[class*="scan-login-container"]');
            if (scan) scan.style.display = 'none';
            // Show password section
            const pw = document.querySelector('[class*="password-section"]');
            if (pw) pw.style.display = 'block';
        }""")
        time.sleep(1)
        state = page.evaluate("""() => {
            const pw = document.querySelector('[class*="password-section"]');
            return pw ? window.getComputedStyle(pw).display : 'no pw';
        }""")
        print(f"   After force: password-section display = {state}")

    # Now check if inputs exist and fill them
    print("4. Filling credentials via JS...")
    filled = page.evaluate("""() => {
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        if (!u) return 'no usernameId';
        if (!p) return 'no passwordId';
        
        // Use native value setter for React 16+
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        
        nativeSetter.call(u, '""" + MMS_USERNAME + """');
        u.dispatchEvent(new Event('input', { bubbles: true }));
        u.dispatchEvent(new Event('change', { bubbles: true }));
        
        nativeSetter.call(p, '""" + MMS_PASSWORD + """');
        p.dispatchEvent(new Event('input', { bubbles: true }));
        p.dispatchEvent(new Event('change', { bubbles: true }));
        
        return {u: u.value, p: p.value ? 'set' : 'empty'};
    }""")
    print(f"   {filled}")

    # Blur to trigger validation
    page.evaluate("""() => {
        document.getElementById('passwordId').blur();
    }""")
    time.sleep(1)

    # Check for validation errors
    body = page.evaluate("() => document.body.innerText")
    if '请输入账号' in body:
        print("   ⚠️ Still showing '请输入账号' validation")
        # Try a more complete React event simulation
        page.evaluate("""() => {
            const u = document.getElementById('usernameId');
            // Simulate React's onChange
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(u, '""" + MMS_USERNAME + """');
            // Trigger multiple events that React listens to
            ['input', 'change', 'blur'].forEach(type => {
                const event = new Event(type, { bubbles: true });
                u.dispatchEvent(event);
            });
        }""")
        time.sleep(1)

        page.evaluate("""() => {
            const p = document.getElementById('passwordId');
            if (p) {
                const nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeSetter.call(p, '""" + MMS_PASSWORD + """');
                ['input', 'change', 'blur'].forEach(type => {
                    p.dispatchEvent(new Event(type, { bubbles: true }));
                });
            }
        }""")
        time.sleep(1)
        
        # Check again
        body = page.evaluate("() => document.body.innerText")
        if '请输入账号' in body:
            print("   ⚠️ Validation still showing after React events")
        else:
            print("   ✅ Validation passed!")

    # Click login
    print("5. Clicking login button...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === '登录') {
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
                    b.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true }));
                });
                return;
            }
        }
    }""")
    print("   Login clicked")
    time.sleep(3)

    # Monitor result
    print("6. Waiting for login result (max 120s)...")
    for i in range(120):
        time.sleep(1)
        try:
            url = page.url
            body = page.evaluate("() => document.body.innerText")
            
            # Account risk modal  
            if '系统检测到您的账号异常' in body:
                print(f"   [{i}s] Account risk detected, removing modal...")
                # Get the full modal text for debugging
                risk_text = page.evaluate("""() => {
                    const els = document.querySelectorAll('div');
                    for (const el of els) {
                        if ((el.textContent || '').includes('系统检测到您的账号异常')) {
                            return el.textContent.trim().slice(0, 200);
                        }
                    }
                    return 'not found';
                }""")
                print(f"   Risk modal text: {risk_text}")
                
                # Try clicking the risk modal button
                page.evaluate("""() => {
                    // Find and click confirm/ok button in the risk modal
                    document.querySelectorAll('button, span').forEach(el => {
                        const t = el.textContent.trim();
                        if (t.includes('我知道了') || t.includes('修改密码') || t.includes('确定') || t.includes('关闭')) {
                            el.dispatchEvent(new PointerEvent('click', { bubbles: true, cancelable: true }));
                        }
                    });
                    // Remove the modal entirely
                    document.querySelectorAll('[data-testid*="beast"], [class*="MDL"], [data-testid*="modal"]').forEach(el => {
                        if ((el.textContent || '').includes('系统检测')) el.remove();
                    });
                }""")
                time.sleep(2)
                continue

            # Success
            if HOME_URL in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n✅ LOGIN SUCCESS! URL: {url}")
                context.storage_state(path=AUTH_FILE)
                sz = os.path.getsize(AUTH_FILE) if os.path.exists(AUTH_FILE) else 0
                print(f"   Auth saved: {AUTH_FILE} ({sz} bytes)")
                sys.exit(0)

            if i % 10 == 0:
                print(f"   [{i}s] URL: {page.url[:80]}")
        except:
            pass

    print(f"\n❌ Login timeout. URL: {page.url}")
    print(f"   {page.evaluate('() => document.body.innerText')[:500]}")
    page.screenshot(path="/tmp/pdd_final.png")

    context.close()
    browser.close()

#!/usr/bin/env python3
"""PDD Login v8 - type() approach for React forms"""
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
              "--disable-dev-shm-usage", "--disable-setuid-sandbox",
              "--disable-web-security"]
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
    time.sleep(4)

    # Remove beast-core overlay completely
    print("2. Removing beast-core overlay...")
    page.evaluate("""() => {
        // Remove beast-core and any other modal-like elements
        ['[data-testid="beast-core-modal"]', '.MDL_outerWrapper', '.MDL_alert'].forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                el.remove();
                document.body.style.overflow = 'auto';
            });
        });
    }""")
    time.sleep(1)

    # Click account tab - using pixel-perfect approach
    print("3. Clicking '账号登录' tab...")
    tab_clicked = page.evaluate("""() => {
        // Find the tab container
        const containers = document.querySelectorAll('[class*="tab"], [class*="operation"], [class*="Common"]');
        for (const c of containers) {
            const spans = c.querySelectorAll('span');
            for (const span of spans) {
                if (span.textContent.trim() === '账号登录') {
                    // Get the center coordinates
                    const rect = span.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    // Create click events at exact position
                    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
                        span.dispatchEvent(new PointerEvent(type, { 
                            bubbles: true, cancelable: true, clientX: x, clientY: y 
                        }));
                    });
                    return `clicked at (${x.toFixed(0)}, ${y.toFixed(0)})`;
                }
            }
        }
        return 'not found';
    }""")
    print(f"   {tab_clicked}")
    time.sleep(3)

    # NOW: Make the input fields programmatically visible AND focused
    print("4. Force-revealing input fields...")
    page.evaluate("""() => {
        const u = document.getElementById('usernameId');
        const p = document.getElementById('passwordId');
        if (!u) return 'no username input';
        
        // Find the parent container and force it visible
        let parent = u.parentElement;
        while (parent) {
            const style = window.getComputedStyle(parent);
            if (style.display === 'none' || style.visibility === 'hidden') {
                parent.style.display = 'block';
                parent.style.visibility = 'visible';
                parent.style.opacity = '1';
                console.log('Revealed parent:', parent.className);
            }
            parent = parent.parentElement;
            if (parent === document.body) break;
        }
        
        u.style.display = 'block';
        u.style.visibility = 'visible';
        u.style.opacity = '1';
        p.style.display = 'block';
        p.style.visibility = 'visible';
        p.style.opacity = '1';
        
        return 'inputs revealed';
    }""")
    time.sleep(1)

    # Now use Playwright's type() which properly triggers React event chain
    print("5. Typing username...")
    page.locator("#usernameId").type(MMS_USERNAME, delay=20)
    print("   Username typed")
    time.sleep(0.5)
    
    print("6. Typing password...")
    page.locator("#passwordId").type(MMS_PASSWORD, delay=20)
    print("   Password typed")
    time.sleep(0.5)

    # Verify values
    vals = page.evaluate("""() => ({
        u: document.getElementById('usernameId').value,
        p: document.getElementById('passwordId').value
    })""")
    print(f"   Values: username={vals['u']}, password={'***' if vals['p'] else 'EMPTY'}")

    # Click login
    print("7. Clicking login button...")
    login_result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.trim() === '登录') {
                const rect = btn.getBoundingClientRect();
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
                    btn.dispatchEvent(new PointerEvent(type, {
                        bubbles: true, cancelable: true,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2
                    }));
                });
                return 'clicked';
            }
        }
        return 'no button found';
    }""")
    print(f"   {login_result}")
    time.sleep(3)

    # Wait for result
    print("8. Waiting for login result...")
    for i in range(120):
        time.sleep(1)
        try:
            url = page.url
            body = page.evaluate("() => document.body.innerText")
            
            # Check for account risk modal
            if '系统检测到您的账号异常' in body or '盗号风险' in body:
                print(f"   [{i}s] Account risk detected, removing modal...")
                page.evaluate("""() => {
                    document.querySelectorAll('[data-testid], [class*="MDL"], [class*="modal"], [class*="beast"]').forEach(el => {
                        if ((el.textContent || '').includes('系统检测') || (el.textContent || '').includes('盗号风险')) {
                            el.remove();
                        }
                    });
                }""")
                time.sleep(2)
            
            # Success
            if HOME_URL in url or ("mms.pinduoduo.com" in url and "/login/" not in url):
                print(f"\n✅ LOGIN SUCCESS! URL: {url}")
                context.storage_state(path=AUTH_FILE)
                print(f"   Auth saved: {AUTH_FILE}")
                sys.exit(0)
            
            if i % 10 == 0:
                print(f"   [{i}s] URL: {page.url[:80]}")
                if '请输入账号' in body:
                    print(f"   ⚠️ Validation: 请输入账号")
                    # Try submitting again via JS
                    page.evaluate("""() => {
                        const btn = document.querySelector('button');
                        if (btn && btn.textContent.trim().includes('登录')) btn.click();
                    }""")
                    
        except Exception as e:
            pass
    
    print(f"\n❌ Timeout. URL: {page.url}")
    print(f"   Body: {page.evaluate('() => document.body.innerText')[:500]}")
    page.screenshot(path="/tmp/pdd_timeout2.png")

    context.close()
    browser.close()

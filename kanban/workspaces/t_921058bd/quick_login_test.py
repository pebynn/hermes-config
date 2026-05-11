#!/usr/bin/env python3
"""Quick PDD login test with detailed output"""
import sys, os, time, json
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://mms.pinduoduo.com/login/"
AUTH_FILE = os.path.expanduser("~/.pdd_auth.json")
MMS_USERNAME = os.environ.get("MMS_USERNAME", "18125973593")
MMS_PASSWORD = os.environ.get("MMS_PASSWORD", "Aa123456")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
        user_agent="Mozilla/5.0 Chrome/120.0.0.0"
    )
    page = context.new_page()
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    # Remove beast-core
    page.evaluate("""() => {
        document.querySelectorAll('[data-testid*="beast"], [class*="MDL"], [class*="modal"]').forEach(e => e.remove());
    }""")
    time.sleep(1)
    
    # Switch to account login and fill via Playwright's locator click approach  
    # First check which tab is visible
    tab_text = page.evaluate("""() => {
        const el = document.querySelector('[class*="tab"]');
        return el ? el.textContent.trim() : 'no tab';
    }""")
    print(f"Tab bar: {tab_text[:80]}")
    
    # Click the tab area using evaluate with position
    page.evaluate("""() => {
        const containers = document.querySelectorAll('span');
        for (const span of containers) {
            if (span.textContent.trim() === '账号登录') {
                span.click();
                return;
            }
        }
    }""")
    time.sleep(2)
    
    # Try to use Playwright's fill - it might work now since the input might be in the DOM
    try:
        page.fill("#usernameId", MMS_USERNAME, timeout=5000)
        print("fill() username: OK")
        page.fill("#passwordId", MMS_PASSWORD, timeout=5000)
        print("fill() password: OK")
    except Exception as e:
        print(f"fill() failed: {str(e)[:100]}")
        # Try type() instead
        page.locator("#usernameId").type(MMS_USERNAME, delay=10)
        print("type() username: done")
        page.locator("#passwordId").type(MMS_PASSWORD, delay=10)
        print("type() password: done")
    
    time.sleep(0.5)
    
    # Verify values
    vals = page.evaluate("""() => ({
        u: document.getElementById('usernameId').value,
        p: document.getElementById('passwordId').value
    })""")
    print(f"Values: u='{vals['u']}', p='{'*'*len(vals['p'])}'")
    
    # Submit via JS
    print("Submitting login...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === '登录') {
                b.click();
                return;
            }
        }
    }""")
    time.sleep(5)
    
    # Check result
    url = page.url
    body = page.evaluate("() => document.body.innerText")
    print(f"URL: {url}")
    print(f"Body (first 500): {body[:500]}")
    
    # Take screenshot in PNG (smaller) 
    page.screenshot(path="/tmp/pdd_quick.png", full_page=False)
    print("Screenshot: /tmp/pdd_quick.png")
    
    # Try detecting risk modal and bypassing
    if '系统检测' in body:
        print("ACCOUNT RISK MODAL DETECTED - trying to bypass...")
        page.evaluate("""() => {
            // Click all buttons in the modal
            document.querySelectorAll('button, span, a').forEach(el => {
                const text = (el.textContent || '').trim();
                if (text.includes('修改密码') || text.includes('我知道了') || text.includes('稍后')) {
                    el.click();
                }
            });
            // Remove all modals
            document.querySelectorAll('[class*="MDL"], [data-testid*="beast"], [class*="modal"], [class*="dialog"]').forEach(e => e.remove());
        }""")
        time.sleep(2)
        body = page.evaluate("() => document.body.innerText")
        print(f"After bypass: {body[:300]}")
    
    context.close()
    browser.close()

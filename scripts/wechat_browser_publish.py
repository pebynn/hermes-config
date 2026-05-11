#!/usr/bin/env python3
"""Publish to WeChat MP draft using Playwright + saved cookies."""
import sys, json, re, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIE_FILE = Path.home() / ".hermes" / "credentials" / "wechat_cookies.json"
HTML_DIR = Path.home() / "writing-data" / "published-html"

def publish(date_str, html_path=None, title=None, content=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
        )
        
        # Load saved cookies
        cookies = json.loads(COOKIE_FILE.read_text())
        # Need to add 'httpOnly' and 'secure' if missing for Playwright
        for c in cookies:
            if 'httpOnly' not in c: c['httpOnly'] = True
            if 'secure' not in c: c['secure'] = True
            if 'sameSite' not in c: c['sameSite'] = 'Lax'
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            no_viewport=False,
        )
        context.add_cookies(cookies)
        page = context.new_page()
        
        # Go to home page first to establish session
        page.goto("https://mp.weixin.qq.com/", timeout=30000)
        time.sleep(3)
        print(f"Home URL: {page.url[:80]}")
        
        # Check if logged in
        if "cgi-bin/home" in page.url:
            print("✅ Logged in via cookies!")
        else:
            print("⚠️ Not logged in, need manual login")
            for i in range(90):
                time.sleep(2)
                if "cgi-bin/home" in page.url:
                    print("✅ Login detected!")
                    break
            
        if "cgi-bin/home" not in page.url:
            print("❌ Login failed")
            browser.close()
            return False
        
        # Extract token from URL
        token_match = re.search(r'token=(\d+)', page.url)
        token = token_match.group(1) if token_match else ""
        print(f"Token: {token}")
        
        # Save the full cookie set again (might have new cookies from login)
        updated_cookies = context.cookies()
        COOKIE_FILE.write_text(json.dumps(updated_cookies, indent=2, ensure_ascii=False))
        print(f"Saved {len(updated_cookies)} cookies")
        
        # Navigate to editor
        editor_url = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&type=77&isNew=1&lang=zh_CN"
        page.goto(editor_url, timeout=30000)
        time.sleep(5)  # Let SPA render
        
        print(f"Editor URL: {page.url[:80]}")
        
        # Fill title - try multiple selectors
        title_selectors = [
            "input#title",
            "#title", 
            "input[placeholder*='标题']",
            "input[name='title']",
        ]
        for sel in title_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el:
                    el.click()
                    el.fill("")
                    page.keyboard.insert_text(title)
                    print(f"Title filled via: {sel}")
                    break
            except: 
                traceback.print_exc()
                pass
        
        # Use browser JS to set content via the editor's API
        # Try to find and click the HTML mode button
        html_btns = ["text=HTML", "a.*html.*", "button.*html.*"]
        found_html = False
        for btn_text in ["HTML", "html"]:
            try:
                btn = page.get_by_text(btn_text, exact=True).first
                if btn:
                    btn.click()
                    time.sleep(1)
                    # Now fill the textarea
                    ta = page.wait_for_selector("textarea", timeout=3000)
                    if ta:
                        ta.fill(content)
                        found_html = True
                        print("Filled content via HTML mode textarea")
                        break
            except: 
                traceback.print_exc()
                pass
        
        if not found_html:
            # Try to use JS to access the editor
            try:
                page.evaluate(f"""
                    // Try to access the rich editor via window
                    var editor = document.querySelector('.rich_media_content') || 
                                document.querySelector('[contenteditable]') || 
                                document.querySelector('iframe')?.contentDocument?.body;
                    if (editor) editor.innerHTML = {json.dumps(content)};
                """)
                print("Filled content via JS eval")
            except Exception as e:
                print(f"JS eval failed: {e}")
        
        # Click save button
        for btn_text in ["保存", "保存并发布", "提交"]:
            try:
                btn = page.get_by_text(btn_text, first=True)
                if btn:
                    btn.click()
                    time.sleep(3)
                    print(f"Clicked save button: {btn_text}")
                    
                    # Wait for success indicator
                    for i in range(10):
                        time.sleep(1)
                        # Check for success message
                        try:
                            success = page.query_selector(".weui-dialog__bd, .msg, .success, [class*='success']")
                            if success:
                                print(f"✅ {success.text_content()}")
                                browser.close()
                                return True
                        except:
                            traceback.print_exc()
                            pass
                    break
            except:
                traceback.print_exc()
                pass
        
        print("⚠️ Save may have succeeded, check wechat manually")
        time.sleep(3)
        browser.close()
        return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    
    title = f"A股复盘 {args.date}"
    content = "<p>test content</p>"
    publish(args.date, title=title, content=content)

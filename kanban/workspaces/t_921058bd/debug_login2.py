#!/usr/bin/env python3
"""Debug PDD login - check all interactive elements on the risk page"""
import sys, os, time, json
sys.path.insert(0, os.path.expanduser("~/PDD"))
from pdd_login_v2 import _inject_stealth
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://mms.pinduoduo.com/login/"
MMS_USERNAME = os.environ.get("MMS_USERNAME", "18125973593")
MMS_PASSWORD = os.environ.get("MMS_PASSWORD", "Aa123456")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
    )
    page = context.new_page()
    _inject_stealth(page)

    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    # Switch to account login tab
    tabs = page.query_selector_all('[class*="login"]')
    for t in tabs:
        text = (t.text_content() or "").strip()
        if "账号" in text or "密码" in text:
            t.click()
            time.sleep(1)
            break
    
    # Fill credentials
    page.fill("input[type='text']", MMS_USERNAME)
    page.fill("input[type='password']", MMS_PASSWORD)
    time.sleep(1)
    
    # Click login
    page.click("button")
    time.sleep(5)
    
    # NOW let's see what's on the page
    print("=== URL ===")
    print(page.url)
    
    print("\n=== All buttons and links ===")
    els = page.evaluate("""() => {
        const items = document.querySelectorAll('button, a, span[role="button"], div[role="button"], [class*="btn"], [class*="button"]');
        return Array.from(items).slice(0,30).map(el => ({
            tag: el.tagName,
            text: (el.textContent || '').trim().slice(0,50),
            class: (el.className || '').slice(0,60),
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect()
        }));
    }""")
    for el in els:
        print(f'  {el["tag"]:6s} visible={el["visible"]:5} rect=({el["rect"]["x"]:.0f},{el["rect"]["y"]:.0f},{el["rect"]["width"]:.0f}x{el["rect"]["height"]:.0f}) text="{el["text"]}" class="{el["class"]}"')

    print("\n=== All inputs ===")
    inputs = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('input')).map(el => ({
            type: el.type,
            placeholder: el.placeholder,
            name: el.name,
            id: el.id,
            visible: el.offsetParent !== null
        }));
    }""")
    for inp in inputs:
        print(f'  type={inp["type"]:10s} placeholder="{inp["placeholder"]}" name="{inp["name"]}" visible={inp["visible"]}')

    print("\n=== Full page text (key sections) ===")
    body = page.evaluate("() => document.body.innerText")
    print(body[:2000])
    
    # Try clicking any "close" or "skip" or "continue" buttons
    print("\n=== Trying to find close/skip/continue buttons ===")
    for text in ["关闭", "跳过", "继续", "知道了", "确定", "取消", "稍后"]:
        try:
            btn = page.locator(f'text="{text}"')
            count = btn.count()
            if count > 0:
                print(f'  Found "{text}" button: {count} instances')
        except:
            pass
    
    context.close()
    browser.close()

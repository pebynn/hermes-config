#!/usr/bin/env python3
"""Debug PDD login - check what happens after submitting credentials"""
import sys, os, time, json
sys.path.insert(0, os.path.expanduser("~/PDD"))
from pdd_login_v2 import (
    _switch_to_account_tab, _fill_login_form, _click_login_button,
    _is_slider_captcha, _try_solve_slider, _inject_stealth
)
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://mms.pinduoduo.com/login/"
HOME_URL = "https://mms.pinduoduo.com/home/"
MMS_USERNAME = os.environ.get("MMS_USERNAME", "18125973593")
MMS_PASSWORD = os.environ.get("MMS_PASSWORD", "Aa123456")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="zh-CN", timezone_id="Asia/Shanghai",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    _inject_stealth(page)

    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    print(f"1. Login page loaded. URL: {page.url}")
    page.screenshot(path="/tmp/pdd_debug_1.png")

    _switch_to_account_tab(page)
    time.sleep(2)
    page.screenshot(path="/tmp/pdd_debug_2.png")

    _fill_login_form(page, MMS_USERNAME, MMS_PASSWORD)
    time.sleep(1)
    page.screenshot(path="/tmp/pdd_debug_3.png")

    _click_login_button(page)
    print("2. Login button clicked")
    time.sleep(5)

    # Check what happened
    page.screenshot(path="/tmp/pdd_debug_4.png")
    url_after = page.url
    print(f"3. URL after 5s: {url_after}")
    print(f"4. Is slider captcha: {_is_slider_captcha(page)}")
    print(f"5. Page title: {page.title()}")

    # Get page text content for error messages
    body_text = page.evaluate("() => document.body.innerText")
    print(f"6. Page text (first 1000 chars): {body_text[:1000]}")

    # Try slider if present
    if _is_slider_captcha(page):
        print("7. Slider captcha detected, attempting to solve...")
        solved = _try_solve_slider(page)
        print(f"   Solved: {solved}")
        time.sleep(3)
        page.screenshot(path="/tmp/pdd_debug_5.png")
        print(f"   URL after slider: {page.url}")

    # Check for mms session cookies
    cookies = context.cookies()
    pdd_cookies = [c for c in cookies if "pinduoduo" in (c.get("domain","") or "")]
    print(f"\n8. PDD cookies after login: {len(pdd_cookies)}")
    for c in pdd_cookies:
        n, v = c["name"], c.get("value","")
        print(f"   {n}: {v[:40]}..." if len(v)>40 else f"   {n}: {v}")

    context.close()
    browser.close()

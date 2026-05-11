#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
print("sync_api imported OK")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    print("chromium launched OK")
    browser.close()
print("ALL OK")

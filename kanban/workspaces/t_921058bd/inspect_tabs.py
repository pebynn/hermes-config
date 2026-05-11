#!/usr/bin/env python3
"""Inspect PDD login tab DOM structure in detail"""
import sys, os, time, json
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://mms.pinduoduo.com/login/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    page = context.new_page()
    
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    
    # Remove beast-core
    page.evaluate("""() => {
        document.querySelectorAll('[data-testid*="beast"], [class*="MDL"], [class*="modal"]').forEach(e => e.remove());
    }""")
    time.sleep(1)
    
    # Detailed inspection of the tab/login area
    print("=== Tab area HTML ===")
    html = page.evaluate("""() => {
        // Find elements containing login-related text
        const containers = document.querySelectorAll('[class*="tab"], [class*="login"], [class*="operation"]');
        let result = '';
        for (const c of containers) {
            const rect = c.getBoundingClientRect();
            if (rect.width > 50 && rect.height > 10) {
                result += `\\n--- ${c.tagName}.${(c.className+'').slice(0,60)} (${rect.width}x${rect.height}) ---\\n`;
                // List all text nodes and child elements
                c.querySelectorAll('*').forEach(child => {
                    const t = (child.textContent || '').trim();
                    if (t && t.length < 60) {
                        result += `  ${child.tagName}.${(child.className+'').slice(0,40)}: "${t}"\\n`;
                    }
                });
            }
        }
        return result || 'No container found';
    }""")
    print(html[:2000])

    # Get the login view HTML skeleton
    print("\n=== Login view area HTML ===")
    view = page.evaluate("""() => {
        const section = document.querySelector('section');
        if (!section) return 'no section';
        return section.innerHTML.slice(0, 2000).replace(/</g, '&lt;');
    }""")
    print(view[:2000])
    
    context.close()
    browser.close()

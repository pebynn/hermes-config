#!/usr/bin/env python3
try:
    import playwright
    print(f"playwright module: {playwright.__version__}")
    from playwright.sync_api import sync_playwright
    print("sync_api: OK")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")

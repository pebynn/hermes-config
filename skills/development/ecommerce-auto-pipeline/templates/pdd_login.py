#!/usr/bin/env python3
"""
拼多多商家后台登录脚本 (scrapling StealthySession)

首次登录:  python3 pdd_login.py
无界面复用: python3 pdd_login.py --headless
仅检查会话: python3 pdd_login.py --check-only
导出 Cookie: python3 pdd_login.py --export-cookies

环境变量:
  MMS_USERNAME  拼多多商家后台用户名
  MMS_PASSWORD  密码
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from scrapling.fetchers import StealthySession

# ---- 配置 ----
LOGIN_URL = "https://mms.pinduoduo.com/login/"
HOME_URL = "https://mms.pinduoduo.com/home/"
PROFILE_DIR = str(Path.home() / ".pdd_browser_profile")
COOKIE_FILE = str(Path.home() / ".pdd_cookies.json")


def get_credentials(args) -> tuple[str, str]:
    """获取凭据: 命令行 > 环境变量 > 占位符"""
    username = args.username or os.getenv("MMS_USERNAME", "your_username_here")
    password = args.password or os.getenv("MMS_PASSWORD", "your_password_here")
    if username == "your_username_here":
        print("[WARN] 使用占位符账号，请通过 --username/--password 或环境变量指定")
    return username, password


def login_page_action(username: str, password: str):
    """page_action: 在登录页执行账号密码登录"""

    def action(page: Page):
        # 1. 切换到账号密码登录 Tab
        try:
            page.click('text=账号登录', timeout=3000)
        except PlaywrightTimeout:
            try:
                page.click('text=密码登录', timeout=3000)
            except PlaywrightTimeout:
                print("[INFO] 可能已在账号密码登录模式，跳过 Tab 切换")

        time.sleep(1)

        # 2. 填入账号密码
        page.fill("#usernameId", username)
        page.fill("#passwordId", password)

        # 3. 点击登录
        page.click('button:has-text("登录")')

        # 4. 检测滑块验证码
        time.sleep(2)
        try:
            captcha = page.query_selector(".captcha")
            if captcha and captcha.is_visible():
                print("\n>>> 检测到滑块验证码，请手动完成，完成后按 Enter 继续...")
                input()
        except Exception:
            pass

        # 5. 等待登录完成
        try:
            page.wait_for_url("**/home/**", timeout=15000)
            print("[OK] 登录成功")
        except PlaywrightTimeout:
            current_url = page.url
            if "/login/" not in current_url:
                print(f"[OK] 疑似登录成功 (URL: {current_url})")
            else:
                print(f"[WARN] 登录未完成，当前 URL: {current_url}")

    return action


def check_session(session: StealthySession) -> bool:
    """检查当前会话是否有效（是否已登录）"""
    try:
        page = session.get(HOME_URL)
        current_url = str(page.url) if hasattr(page, 'url') else ''

        if "/login/" not in current_url:
            print(f"[OK] 会话有效 (URL: {current_url})")
            return True
        else:
            print("[WARN] 会话已过期，需要重新登录")
            return False
    except Exception as e:
        print(f"[ERROR] 检查会话失败: {e}")
        return False


def export_cookies(session: StealthySession):
    """导出 cookies 到 JSON 文件"""
    try:
        cookies = session.cookies() if hasattr(session, 'cookies') else []
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        print(f"[OK] Cookies 已导出到 {COOKIE_FILE}")
    except Exception as e:
        print(f"[ERROR] 导出 Cookies 失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="拼多多商家后台登录")
    parser.add_argument("--headless", action="store_true", help="无界面模式")
    parser.add_argument("--export-cookies", action="store_true", help="登录后导出 cookies")
    parser.add_argument("--check-only", action="store_true", help="仅检查会话有效性")
    parser.add_argument("--username", help="商家后台用户名")
    parser.add_argument("--password", help="密码")
    args = parser.parse_args()

    username, password = get_credentials(args)

    # 创建 StealthySession
    session = StealthySession(
        headless=args.headless,
        user_data_dir=PROFILE_DIR,
        solve_cloudflare=True,
        hide_canvas=True,
        block_webrtc=True,
        real_chrome=True,
    )

    if args.check_only:
        valid = check_session(session)
        sys.exit(0 if valid else 1)

    # 执行登录
    print(f"[INFO] 打开登录页 ({LOGIN_URL})...")
    page = session.fetch(
        LOGIN_URL,
        page_action=login_page_action(username, password),
    )

    # 检查登录结果
    valid = check_session(session)

    if valid and args.export_cookies:
        export_cookies(session)

    print("[DONE]")


if __name__ == "__main__":
    main()

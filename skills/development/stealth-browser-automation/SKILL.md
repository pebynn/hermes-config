---
author: unknown
description: Build persistent browser sessions with Playwright-based stealth tools
  (scrapling StealthySession, etc.) — login automation, cookie persistence via user_data_dir,
  page_action callbacks, captcha detection/handling, SPA tab switching. NOT for basic
  page scraping; use web-researcher or crawl4ai for that.
name: stealth-browser-automation
---

# Stealth Browser Automation

Class-level patterns for building **persistent browser sessions** using Playwright-based stealth tools like scrapling's `StealthySession`. Covers login flows, cookie persistence, and anti-detection for Chinese e-commerce platforms and similar JS-heavy SPAs.

## When to Use

Use this skill when you need to:
- Build a login script for a JS-heavy SPA (拼多多商家后台, 微信公众号, 1688, etc.)
- Persist browser session (cookies + local storage) across runs via user_data_dir or storage_state
- Automate multi-step login flows (tab switching → form fill → submit → captcha)
- Build a script that recovers from session expiry automatically
- Stealth is required (anti-fingerprinting, cloudflare bypass)
- Fill a React SPA editor with multi-strategy selector fallbacks (WeChat MP drafts, etc.)

Do NOT use for simple scraping — use `web_search`, `jina-reader`, or `crawl4ai` instead.

## Key Concepts

### StealthySession vs StealthyFetcher.fetch()

| Tool | When | Session Persistence |
|------|------|-------------------|
| `StealthySession` ⭐ | Multi-step automation, login flows | Persistent via `user_data_dir` |
| `StealthyFetcher.fetch()` | One-shot page fetch | Creates fresh session each call |

**Always use `StealthySession` for login automation.** Import from `scrapling.fetchers`.

### Cookie Persistence: Two Strategies

Two approaches, choose based on your needs:

| Strategy | Pro | Con | Best for |
|----------|-----|-----|----------|
| `user_data_dir` | Auto-persists ALL browser state (cookies, localStorage, IndexedDB) | Heavy (~100MB); corruption requires full dir nuke | Long-running e-commerce sessions (拼多多商家后台) |
| `storage_state` (JSON) | Lightweight (~3KB); inspectable; portable; explicit save/load | Must save/load explicitly; only captures cookies + localStorage | QR-code login platforms (微信公众号); CI/CD environments |

**When to choose `storage_state`:** The WeChat Official Account backend only needs cookies for auth — local storage, IndexedDB, and cache are disposable. A 3KB JSON file is easier to inspect, backup, and reinitialize than a multi-megabyte browser profile directory.

#### user_data_dir (StealthySession)

The `user_data_dir` parameter points to a browser profile directory. All cookies, local storage, and session data survive across runs:

```python
from scrapling.fetchers import StealthySession

with StealthySession(
    user_data_dir="~/.my_app_browser",
    headless=False,  # headful for first login
) as session:
    response = session.fetch("https://target.com/login")
```

First run: headful (user interacts with captcha, 2FA, etc.)  
Subsequent runs: headless (session auto-restores)

#### storage_state (Raw Playwright + JSON)

For platforms like WeChat MP that use QR-code login, use raw Playwright with explicit storage_state save/load:

```python
from playwright.sync_api import sync_playwright

STORAGE_FILE = Path.home() / ".hermes" / "browser-data" / "platform" / "storage_state.json"
STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context_kwargs = {
        "viewport": {"width": 1280, "height": 800},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }
    if STORAGE_FILE.exists():
        context_kwargs["storage_state"] = str(STORAGE_FILE)

    context = browser.new_context(**context_kwargs)
    page = context.new_page()

    # After login succeeded:
    context.storage_state(path=str(STORAGE_FILE))
```

The `storage_state` JSON can be version-controlled, inspected with `jq`, and easily deleted when tokens expire.

### page_action Callback

The `page_action` parameter takes a callable `(page: Page) -> None` that runs **after** navigation completes. Use it to:

- Switch SPA tabs (e.g., QR → password login mode)
- Fill form fields
- Click submit buttons
- Wait for post-login redirects

```python
def login_action(page):
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)  # let React SPA settle
    
    # Switch tab
    page.get_by_text("账号登录").click()
    time.sleep(1)
    
    # Fill form
    page.fill("#username", user)
    page.fill("#password", pw)
    
    # Submit
    page.get_by_text("登录", exact=True).click()

with StealthySession(page_action=login_action, ...) as session:
    session.fetch(LOGIN_URL)
```

### Session Context Cookie Extraction

After login, extract cookies from the `StealthySession.context` attribute:

```python
with StealthySession(...) as session:
    session.fetch(LOGIN_URL)
    cookies = session.context.cookies()
    
    # Check for session cookies
    if any(c["name"] == "SESSION_ID" for c in cookies):
        print("Logged in!")
```

## Standard Workflow

### Phase 1: First Login (Headful)

1. Create a `StealthySession` with `headless=False`, `user_data_dir=<persistent_dir>`
2. Provide a `page_action` callback that automates the login flow
3. Call `session.fetch(LOGIN_URL)` — page_action fires after navigation
4. After page_action completes, wait for redirect / session cookie appearing
5. Extract cookies via `session.context.cookies()`
6. Verify session by fetching the post-login URL again

### Phase 2: Session Recovery (Headless)

1. Create `StealthySession` with same `user_data_dir`, now `headless=True`
2. Fetch the authenticated page directly (e.g., HOME_URL)
3. Check if redirected back to login — if so, session expired, fall to Phase 1
4. Optional: verify with `--check-only` mode before running automation

### Phase 3: Cookie Export (Portability)

Export cookies from `session.context.cookies()` to a JSON file for inspection/debugging:

```python
import json
with open("cookies.json", "w") as f:
    json.dump(session.context.cookies(), f, indent=2)
```

## Multi-Strategy Selector Fallback

For SPAs where class names change with every deploy (WeChat MP, etc.), use a **fallback chain** for each element rather than a single selector:

```python
def _fill_title(page, title: str) -> bool:
    selectors = [
        "#title",
        "input#title",
        "[name='title']",
        "[placeholder='请输入标题']",
        "input[placeholder*='标题']",
    ]
    for selector in selectors:
        try:
            el = page.wait_for_selector(selector, timeout=3000)
            if el:
                el.click()
                el.fill("")
                page.keyboard.insert_text(title)
                return True
        except Exception:
            continue
    return False  # All fallbacks failed
```

**Priority order** (recommended):
1. `page.get_by_text(...)` — text matching (most stable)
2. `page.locator("[id='...']")` — ID selectors (when IDs are stable)
3. `page.locator("button", has_text=re.compile(r"保存|提交"))` — role + text regex
4. `page.wait_for_selector("[placeholder*='...']")` — placeholder partial match
5. `page.wait_for_selector("[class*='...']")` — CSS class partial match (last resort, class names change most often)

## Login Detection by URL Pattern

Some platforms (WeChat MP, 智谱) use QR-code login with automatic redirects. Detect login by watching the URL, not by looking for page elements:

```python
def _check_logged_in(page) -> bool:
    url = page.url
    if "cgi-bin/home" in url or "cgi-bin/indexpage" in url:
        return True
    if "token=" in url and "login" not in url.lower():
        return True
    # Fallback: user avatar element
    try:
        page.wait_for_selector(
            ".account, .user-info, [class*='user_avatar']",
            timeout=5000
        )
        return True
    except Exception:
        return False
```

## Anti-Detection Settings

Always apply these for Chinese e-commerce platforms:

```python
session_kwargs = {
    "headless": ...,
    "hide_canvas": True,        # Canvas fingerprint randomization
    "block_webrtc": True,       # Prevent IP leak via WebRTC
    "solve_cloudflare": True,   # Auto-solve Turnstile challenges
    "real_chrome": True,        # Use system Chrome, reduces detection
    "network_idle": True,       # Wait for all network activity to settle
    "user_data_dir": ...,
    "timeout": 60000,           # Longer timeout for slow SPAs
}
```

## Pitfalls

- **SingletonLock/SingletonCookie stale files block re-launch**: When a Playwright persistent context (`launch_persistent_context` or `user_data_dir`) is killed, times out, or crashes, Chrome leaves lock files (`SingletonLock`, `SingletonCookie`, `SingletonSocket`) in the profile directory. These block any new Chromium instance from using that directory. Fix before re-launch: `rm -f <user_data_dir>/Singleton*`. Always check for these when user reports "浏览器未正常打开" on a re-launch attempt.

- **QR login detection may miss redirect paths**: After QR scan, some platforms (WeChat MP) redirect through intermediate URLs before reaching the expected post-login page. The `page.url in` check for specific paths (e.g., "cgi-bin/home") may time out while the redirect chain is still in progress. Use a broader set of patterns: `any(p in page.url for p in ["cgi-bin/", "token=", "home", "indexpage"])`. Also consider `page.wait_for_url(re.compile("cgi-bin|token="), timeout=...)` as a fallback after the polling loop expires.

- **launch_persistent_context vs launch for cookie extraction**: `p.chromium.launch()` creates a fresh temp profile every time — cookies from previous sessions are lost. To extract cookies from an existing profile (e.g., `~/.hermes/browser-data/wechat-mp/`), use `p.chromium.launch_persistent_context(user_data_dir=path)` which loads the existing profile state. Without this, even a headful login produces an empty or very short cookie set because the session is in a throwaway profile.

- **SPA rendering delay**: Always `time.sleep(1–2)` after `wait_for_load_state("domcontentloaded")`. React SPAs need a tick to render after the DOM loads.
- **`networkidle` trap**: Modern SPAs with persistent WebSocket, SSE, or long-poll connections NEVER reach `networkidle`. Always use `wait_for_load_state("load")` instead of `"networkidle"` for Chinese SaaS platforms (智谱, 阿里云百炼, etc.). The `load` event fires once all initial resources finish — pair with `asyncio.sleep(2-3)` for SPA render settling. If a page hangs for 60s on `networkidle`, this is the cause.
- **React event interception**: Some Chinese platforms (雪球 xueqiu.com) intercept ALL synthetic click events — even Playwright headful `el.click()`, `page.mouse.click()`, and `el.dispatchEvent()` fail silently. The page renders, cookies are valid, login is confirmed, but form submission never fires. See `references/xueqiu-anti-bot-findings.md` for full investigation. For such platforms, accept the limitation and build a local-backup fallback workflow.
- **Editor opens in popup (WeChat MP)**: WeChat MP 编辑器不在同页跳转——点击"文章"后在新标签页(popup)打开。必须用 `context.expect_page()` 拦截，不能直接 `page.goto()` 编辑页URL。详见 `references/wechat-mp-publishing.md`。
- **ms-playwright chromium vs snap chromium (Ubuntu Wayland)**: Ubuntu 24.04 Wayland环境下ms-playwright chromium无法加载mp.weixin.qq.com（30s超时）。`channel='chromium'`使用snap chromium可正常工作。
- **Selector fragility**: SPA class names change with each deploy. Prefer text matching (`page.get_by_text(...)`) over CSS class selectors.
- **Tab switching**: Some login pages default to QR code mode. Check for a "账号登录" / "密码登录" tab and click it before filling forms.
- **Captcha blocks**: Scrapling can solve Cloudflare Turnstile automatically (`solve_cloudflare=True`). Slider captchas require manual interaction (detect + pause + wait).
- **Viewport too small**: Default 1440x900 may clip login buttons or distort SPA layouts on some Chinese platforms (智谱, 阿里云). Use 1920x1080 as safe default, or make it configurable via `--viewport WxH`.
- **WeChat MP login**: Password login (`a.btn_login`) may be silently blocked by anti-bot detection. QR code login requires user interaction within 5 minutes. Login state must be saved immediately after detection via `context.storage_state()`, or session is lost on process interruption.

- **WeChat MP ProseMirror editor (2026)**: The old UEditor+iframe model is gone. The content editor is now `<div class="ProseMirror">` (DIV contenteditable, NOT iframe). There is NO HTML source textarea — `Ctrl+Shift+H` no longer works. Content must be injected via `page.evaluate()` setting `.ProseMirror.innerHTML` + dispatching an `input` event. The editor opens as a **popup** (new tab) and must be captured with `context.expect_page()`. The `#title` field is now a TEXTAREA (not INPUT). See `a-share-content-automation` skill for the full working flow.

- **Cookie-based API**: WeChat MP internal API (`cgi-bin/operate_appmsg`) uses session cookies (poc_sid), not access_token. Single cookie is insufficient — need full cookie set from logged-in browser session. See `references/wechat-mp-publishing.md` for complete guide.
- **WeChat MP cookie injection**: Full cookie set (~14 items from mp.weixin.qq.com domain) injected via `context.add_cookies()` enables login without QR scanning. Cookies last 7-14 days. Required cookies include: `poc_sid`, `data_bizuin`, `data_ticket`, `slave_sid`, `slave_user`, `bizuin`, `slave_bizuin`, `ua_id`, `uuid`, `wxuin`, `xid`, `mm_lang`, `rand_info`, `_clck`, `_clsk`. Single `poc_sid` alone is insufficient.
- **WeChat MP editor save button**: The save button is `#js_submit` (text "保存为草稿"), NOT a generic "保存" button. `#js_send` is the publish button.
- **WeChat MP ProseMirror content injection**: The editor body is `DIV.ProseMirror` (ProseMirror-based rich text, NOT UEditor iframe). There is NO HTML source mode textarea — `Ctrl+Shift+H` does not create one. The page has only 2 textareas: `#title`(title) and `#js_description`(digest). Using `editor.wait_for_selector('textarea')` will match `#title` and overflow content into the title field. Correct approach: `editor.evaluate("document.querySelector('.ProseMirror').innerHTML = html; ...dispatchEvent(new Event('input'))")`. See `references/wechat-mp-publishing.md`.
- **Playwright channel='chromium' on Wayland**: Ubuntu 24.04 Wayland requires `channel='chromium'` (uses snap chromium). ms-playwright's bundled chromium times out on all page loads. Symlinking chromium versions may allow launch but page navigation still fails.
- **Multi-cookie auth**: Platforms like 雪球 require 5+ cookies (xq_a_token + xq_r_token + xq_id_token + xq_is_login + u + WAF tokens) — not just the obvious access token. Export ALL cookies from the browser, not individual tokens. See `references/xueqiu-anti-bot-findings.md`.
- **user_data_dir cleanup**: If something breaks, delete the directory and re-do headful login. Session data can get corrupted.
- **`channel='chromium'` for Wayland**: Ubuntu 24.04 Wayland — ms-playwright chromium can't load many Chinese sites (30s timeout on mp.weixin.qq.com). Use `channel='chromium'` to leverage system snap chromium. `p.chromium.launch(channel='chromium', headless=False, args=['--no-sandbox'])`.
- **URL mismatch**: Introduction/info pages often differ from the actual purchase/operation page (e.g., `/coding-plan` vs `/glm-coding`). Always confirm the target URL with the user before writing selectors.
- **Playwright chromium version mismatch**: The venv's playwright may expect a different chromium build than the one cached at `~/.cache/ms-playwright/`. Hermes is updated frequently, and playwright versions pin specific chromium builds (e.g., playwright 1.58.0 → chromium-1208, but 1.56.0 → chromium-1217). Before running `playwright install chromium` (167 MiB download that often times out behind GFW), check what's installed: `ls ~/.cache/ms-playwright/`. If there's a nearby version, try a symlink instead: `ln -sf ~/.cache/ms-playwright/chromium-XXXX ~/.cache/ms-playwright/chromium-YYYY`. The Chromium binary API is very stable across minor build increments — symlinks work reliably.

## Related Skills

- `web-researcher` — for simple scraping (use when you don't need login)
- `crawl4ai` — for crawling content (alternative to this skill)
- `ec-domain` skills — login scripts feed into e-commerce automation pipelines

## References

- `references/pdd-login-pattern.md` — PDD 商家后台登录具体实现模式
- `references/react-beastcore-interaction.md` — React BeastCore 组件自动化交互指南
- `references/python-async-indentation-pitfall.md` — Python async with 缩进错误诊断与修复
- `references/sniper-pattern.md` — Timing-critical purchase sniping
- `references/wechat-mp-publishing.md` — 微信公众号草稿发布：API/IP白名单/浏览器自动化/Cookie直连四种方案及A股数据准确性规则
- `references/wechat-mp-pitfalls.md` — 微信公众号开发中的常见陷阱
- `references/wechat-mp-publish-pattern.md` — 微信公众号发布模式
- `references/wechat-mp-prosemirror.md` — 🆕 微信公众号 ProseMirror 编辑器 Playwright 注入方案 (2026-05-08)
- `references/xueqiu-anti-bot-findings.md` — 雪球 React 前端反自动化检测深度分析（Cookie多因子认证 + WAF + React事件拦截）

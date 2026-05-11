# Purchase Sniper (抢购) Pattern — Raw Playwright

## When to Use

Timing-critical purchase automation (抢购/秒杀) where you must:
- Hit a button within seconds of a known release time (e.g., 09:30:00 daily)
- Maintain logged-in session across runs
- Handle pre- and post-purchase flows (agreement checkbox, confirm dialog, payment QR capture)

## Pattern: Playwright Persistent Context + TimeGate

DO NOT use scrapling's StealthySession for this — it wraps Playwright with abstraction that complicates persistent context debugging. Use raw Playwright `async_playwright()` + `launch_persistent_context()`.

```python
async with async_playwright() as p:
    context = await p.chromium.launch_persistent_context(
        user_data_dir="~/.app-profile",
        headless=False,
        viewport={"width": 1920, "height": 1080},  # 1440x900 too small for some login pages
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = await context.new_page()
    # ... automation ...
```

## Critical Patterns

### 1. Persistent Login via user_data_dir

First run: headful → user manually logs in → close browser.  
Subsequent runs: cookies auto-restored from `user_data_dir`.

Use `--check-only` mode to verify login before the real run.

### 2. TimeGate (Wait Until Exact HH:MM:SS)

```python
async def wait_until_target_time(target: str, refresh_at_minus_5s: bool = True):
    """Wait until HH:MM:SS CST. Optionally refresh 5s before."""
    while True:
        now = datetime.now(CST)
        diff = (target_dt - now).total_seconds()
        if diff <= 0:
            return "target"
        if refresh_at_minus_5s and diff <= 5 and diff > 0:
            return "early_refresh"
        await asyncio.sleep(max(0.1, min(diff, 1)))
```

### 3. Selector Strategy

**Priority order** (for Chinese SPAs where class names change on every deploy):
1. `page.get_by_text("立即抢购")` — Playwright text locator
2. `page.locator("button", has_text=re.compile(r"购买|抢购|订阅"))` — role + text regex
3. `page.query_selector_all("[class*='package-card']")` — partial class match (last resort)

**Always add debug logging** when a selector fails — dump all visible buttons:
```python
all_buttons = await page.query_selector_all("button, [role='button']")
for btn in all_buttons:
    if await btn.is_visible():
        txt = (await btn.inner_text()).strip()
        log.info(f"  '{txt}'")
```

### 4. Page Load Strategy

```python
await page.goto(url, wait_until="domcontentloaded", timeout=60000)
await page.wait_for_load_state("load", timeout=30000)  # NOT networkidle!
await asyncio.sleep(3)  # SPA render settling
```

### 5. Multi-step Purchase Flow with Error Recovery

```
navigate → find card → select plan → check agreement → 
click buy → wait confirm dialog → click confirm → 
wait payment page → select payment method → screenshot QR
```

At each step: screenshot, timeout + retry, dismiss error dialogs.
Use `--dry-run` flag to test selector chain without actual purchase.

### 6. QR Code Capture for WeChat Pay

```python
# Try element-level screenshot first
qr = await page.query_selector("canvas, img[src*='qr'], .qrcode")
if qr:
    await qr.screenshot(path=QRCODE_PATH)
else:
    await page.screenshot(path=QRCODE_PATH)  # fallback: full page
```

## Anti-Detection

```python
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
""")
```

Use `--disable-blink-features=AutomationControlled` in launch args.

## CLI Flags Convention

| Flag | Purpose |
|------|---------|
| `--login` | Open browser, wait for manual login, save session, exit |
| `--check-only` | Open page, screenshot, verify login — no actions |
| `--dry-run` | Full flow up to final click, then stop |
| `--now` | Skip time gate, execute immediately |
| `--target-time HH:MM:SS` | Override default target time |
| `--headless` | Run without GUI |
| `--viewport WxH` | Override viewport (default: 1920x1080) |
| `--billing-cycle month\|year` | For SaaS plans with period switching |
| `--profile-dir PATH` | Override user_data_dir |
| `--clean-profile` | Delete SingletonLock before launch |

## Known Target Pages

| Platform | Purchase URL | Notes |
|----------|-------------|-------|
| 智谱 GLM Coding Plan | `https://www.bigmodel.cn/glm-coding` | Daily 09:30 CST release. Pro plan only (Lite sells out instantly). Element UI + Vue SPA. Persistent WebSocket keeps `networkidle` from firing. Login redirects to `open.bigmodel.cn` then console dashboard — post-login URL ≠ target URL. |

## Login Detection & Manual Login Fallback

### Problem
Persistent context saves cookies but doesn't auto-login. The first run (or after session expiry) needs manual login. Post-login redirect URL may differ from the target purchase page — detecting login by URL alone is unreliable.

### 4-Layer Detection (ensure_logged_in)
```python
async def ensure_logged_in(page) -> bool:
    # 1. URL redirected to login page?
    if re.search(r"/login|/signin|/auth", page.url):
        return await _wait_for_manual_login(page)
    
    # 2. Page text contains "登录" (but NOT "已登录"/"退出登录")
    body = await page.inner_text("body")
    if re.search(r"登录|sign in", body) and not re.search(r"已登录", body):
        return await _wait_for_manual_login(page)
    
    # 3. Package/product cards present? (strongest login indicator)
    if await page.query_selector(".package-card"):
        return True
    
    # 4. Login button visible? (not logged in)
    btn = await page.query_selector("button:has-text('登录')")
    if btn and await btn.is_visible():
        return await _wait_for_manual_login(page)
    
    return True  # assume logged in
```

### Manual Login Waiter (3 Success Indicators)
```python
async def _wait_for_manual_login(page, timeout=300):
    initial_url = page.url
    while time.time() - start < timeout:
        await asyncio.sleep(3)
        
        # Indicator 1: URL changed away from login page
        if not re.search(r"/login|/signin|/auth", page.url) and page.url != initial_url:
            return True
        
        # Indicator 2: User avatar/name appeared
        el = await page.query_selector("[class*='avatar'], [class*='user-name']")
        if el and await el.is_visible():
            return True
        
        # Indicator 3: Package/product cards appeared
        if await page.query_selector(".package-card"):
            return True
    
    return False  # timeout
```

**Key insight**: Post-login redirect target varies by platform (console dashboard, not purchase page). Must detect by *absence of login UI* + *presence of authenticated UI*, not by specific URL.

## Billing Cycle Switching (SPA Tab Pattern)

For SaaS plans with monthly/yearly toggle (智谱, 阿里云百炼, etc.):

```python
async def switch_billing_cycle(page, cycle="month"):
    """Click the monthly/yearly tab before purchasing."""
    keywords = {"month": ["月", "每月", "按月"], "year": ["年", "每年", "按年"]}
    tabs = await page.query_selector_all(".switch-tab-item, [class*='billing-tab']")
    
    for tab in tabs:
        text = await tab.inner_text()
        if any(kw in text for kw in keywords[cycle]):
            cls = await tab.get_attribute("class") or ""
            if "active" in cls:  # already selected
                return True
            await tab.click()  # or tab.evaluate("el => el.click()") as fallback
            return True
    return False
```

Call this **after** finding the plan card **before** clicking the buy button.

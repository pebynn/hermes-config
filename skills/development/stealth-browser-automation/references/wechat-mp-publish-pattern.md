# WeChat Official Account (微信公众号) Draft Publishing Pattern

## When to Use

Publishing articles to a WeChat Official Account draft box when the REST API
(`cgi-bin/draft/add`) is blocked by IP whitelist. Uses browser automation as
a bypass: log in via QR code, fill the React SPA editor, save as draft.

## Pattern: Raw Playwright + storage_state

Do NOT use StealthySession for this. WeChat MP detects session inconsistencies
across restarts. Use raw Playwright with explicit `storage_state` save/load for
maximum control over session boundaries.

### Persistence Strategy: storage_state (not user_data_dir)

| Approach | Pro | Con |
|----------|-----|-----|
| `user_data_dir` | Auto-persists all browser state | Heavy; crashes/corruption require full dir nuke |
| `storage_state` (JSON) | Lightweight (3KB); inspectable; portable | Must save/load explicitly |

**Prefer `storage_state` for WeChat MP.** The editor SPA stores minimal local
state — only cookies + token matter. Save after login, reload on next run.

```python
from playwright.sync_api import sync_playwright

STORAGE_FILE = Path.home() / ".hermes" / "browser-data" / "wechat-mp" / "storage_state.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    context_kwargs = {
        "viewport": {"width": 1280, "height": 800},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }
    if STORAGE_FILE.exists():
        context_kwargs["storage_state"] = str(STORAGE_FILE)

    context = browser.new_context(**context_kwargs)
    page = context.new_page()

    # Anti-detection init script
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] });
    """)

    # After successful login:
    context.storage_state(path=str(STORAGE_FILE))
```

## Login Flow (QR Code)

WeChat MP does NOT support password login via automation. The login page
shows a QR code for the WeChat app to scan.

```python
page.goto("https://mp.weixin.qq.com/", wait_until="domcontentloaded")
time.sleep(2)
page.wait_for_load_state("load", timeout=30000)
time.sleep(2)

# Detect login by watching URL
def _check_logged_in(page) -> bool:
    url = page.url
    if "cgi-bin/home" in url or "cgi-bin/indexpage" in url:
        return True
    if "token=" in url and "login" not in url.lower():
        return True
    # Fallback: check for user avatar element
    try:
        page.wait_for_selector(
            ".account, .account_name, .user-info, "
            "[class*='userInfo'], [class*='user_avatar']",
            timeout=5000
        )
        return True
    except Exception:
        return False

# Poll until logged in (max 5 min)
def _login_flow(page):
    print("请用微信扫描二维码登录微信公众号...")
    start = time.time()
    while time.time() - start < 300:
        if _check_logged_in(page):
            return
        time.sleep(2)
```

**Key timing:** After QR scan, wait ~3-5 seconds for redirect to `/cgi-bin/home`.
Do NOT navigate away — the redirect is automatic.

## Draft Editor Interaction

WeChat MP's draft editor is a React SPA with these components:

```
┌─────────────────────────────────────┐
│  标题:  [________________________]  │
│  作者:  [AI复盘______________]      │
│                                     │
│  ┌─ Toolbar ──────────────────────┐ │
│  │ B I U H1 | [HTML] [保存] [...] │ │
│  └───────────────────────────────┘ │
│  ┌─ Editor Area ─────────────────┐ │
│  │ (rich text or HTML source)    │ │
│  │                                │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Navigation to New Draft

```python
NEW_DRAFT_URL = (
    "https://mp.weixin.qq.com/cgi-bin/appmsg"
    "?t=media/appmsg_edit_v2&action=edit&type=77&isNew=1"
)
page.goto(NEW_DRAFT_URL, wait_until="domcontentloaded", timeout=60000)
time.sleep(2)
page.wait_for_load_state("load", timeout=30000)
time.sleep(3)  # SPA render settling
```

### Multi-Strategy Selector Fallbacks

WeChat MP class names change with every deploy. **Never use class names directly.**
Use this prioritized fallback chain for each element:

#### Title input
```
"#title"
"input#title"
"[name='title']"
"input.rich_media_title"
"[class*='title-input'] input"
"[placeholder='请输入标题']"
"input[placeholder*='标题']"
```

```python
for selector in title_selectors:
    try:
        el = page.wait_for_selector(selector, timeout=3000)
        if el:
            el.click()
            el.fill("")
            page.keyboard.insert_text(title)
            return True
    except Exception:
        continue
```

#### HTML mode toggle
```
"a:has-text('html')"
"button:has-text('html')"
"[class*='toolbar'] a:has-text('html')"
"[class*='switch-html']"
"[data-action='html']"
```

#### Save button
```
"a:has-text('保存')"
"button:has-text('保存')"
"a:has-text('保存草稿')"
"[class*='save'] a"
"[class*='btn_save']"
"[data-action='save']"
```

### Content Pasting (HTML Mode)

After clicking the HTML button, the editor shows a `<textarea>` with raw HTML.
Replace its contents:

```python
page.keyboard.select_all()   # Ctrl+A equivalent
page.keyboard.press("Delete")
el.fill(full_html_content)
```

If the textarea isn't found, try the rich editor's `contenteditable` div:
```python
page.evaluate("""(html) => {
    const el = document.querySelector('#js_rich_editor, .rich_media_area_primary, [contenteditable="true"]');
    if (el) el.innerHTML = html;
}""", html_content)
```

## Image Handling

Local `file://` paths in the HTML (e.g., `src="file:///home/.../chart.png"`)
WILL NOT render in the WeChat editor. You have two options:

**Option A — Upload before publish (recommended for production):**
Use the WeChat REST API (`cgi-bin/material/add_material`) to upload images,
get back `mmbiz.qpic.cn` CDN URLs, and replace all image src attributes.
This is the approach in the existing `publish_draft.py`.

**Option B — Relative paths (works for draft preview, fails on publish):**
Strip `file://` prefixes, keep just the basename. Images won't render in
the official WeChat Reader but the draft structure is correct.

```python
html_content = re.sub(
    r'src="file:///[^"]*/([^"/]+\.(png|jpg|jpeg|gif|svg))"',
    r'src="\1"',
    html_content
)
```

## Debug Mode

When selectors fail (UI changed after deploy), dump the page state:

```python
def _debug_page_state(page):
    print(f"URL: {page.url[:200]}")
    print(f"Title: {page.title()[:100]}")
    for label, selector in [("Title input", "#title"),
                             ("HTML button", "a:has-text('html')"),
                             ("Save button", "a:has-text('保存')"),
                             ("Login button", "#loginBt")]:
        try:
            el = page.wait_for_selector(selector, timeout=1500)
            print(f"  {'✅' if el and el.is_visible() else '❌'} {label}")
        except Exception:
            print(f"  ❌ {label}")
```

## Pitfalls

- **URL redirect detection**: After login, the page may redirect through multiple
  intermediate URLs. Do NOT rely on a single `page.url` match — check for
  multiple patterns (`cgi-bin/home`, `cgi-bin/indexpage`, `token=`).
- **SPA render settling**: The draft editor takes 3-5 seconds to initialize its
  React components after `load` event. If you try to fill the title too early,
  the input element may exist but reject keyboard events.
- **Session expiry**: WeChat MP sessions expire after ~2 hours of inactivity.
  When headless, check login before every publish. If detected as logged out,
  you must fall back to headful + QR scan.
- **HTML mode toggling**: After clicking the HTML button, the textarea may
  animate in. Wait 1.5s before interacting with it.
- **Image CDN URLs**: Pasted `mmbiz.qpic.cn` URLs in HTML source will render
  correctly in the editor preview, but may 403 in the WeChat Reader if the
  image's `media_id` isn't linked to the same account. Test thoroughly.
- **storage_state invalidation**: Some WeChat tokens (like `slave_user` cookie)
  have per-device binding. If you copy `storage_state.json` between machines,
  login may break. Generate fresh state on each machine.

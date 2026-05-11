# Cookie-Based WeChat MP Publishing

## Current Status (2026-05-08)

### ❌ operate_appmsg API — DEPRECATED

`cgi-bin/operate_appmsg` 内部API的草稿创建功能已失效：
- 不带 `sub=create` → `ret=2`（仅列表查询模式，`appmsg_list: []`）
- 带 `sub=create` → `ret=200002 参数错误`
- `cgi-bin/draft/add`、`cgi-bin/operate_draft` → 404

### ✅ Cookie浏览器自动化 — ACTIVE

Cookie不再用于直接API调用，改为注入Playwright进行浏览器自动化。流程：
```
1. 首次：浏览器扫码登录 → DevTools导出完整cookie集 → wechat_cookies.json
2. 后续：Playwright context.add_cookies() → 自动登录 → 编辑器popup → 填写保存
```
详见 `references/browser-publishing.md`。

## 完整Cookie清单

**必须全部提取，缺一不可**（共15+个）：

```
poc_sid, data_bizuin, data_ticket, slave_sid, slave_user,
bizuin, slave_bizuin, ua_id, uuid, wxuin, xid, mm_lang,
rand_info, _clck, _clsk
```

保存格式（Playwright兼容）：
```json
[
  {"name": "poc_sid", "value": "...", "domain": "mp.weixin.qq.com", "path": "/"},
  {"name": "data_bizuin", "value": "3692302149", "domain": "mp.weixin.qq.com", "path": "/"},
  ...
]
```

## 提取方法

### 方法1：浏览器DevTools（推荐，本次使用）

Chrome已登录 → F12 → Application → Cookies → mp.weixin.qq.com → 手动导出所有cookie。

### 方法2：Playwright扫码提取（需要桌面环境）

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chromium', headless=False, args=['--no-sandbox'])
    context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="zh-CN")
    page = context.new_page()
    page.goto("https://mp.weixin.qq.com/")
    # 手动扫码...
    # URL跳转到 cgi-bin/home 即成功
    cookies = context.cookies()
```

## Cookie有效期

7-14天。`poc_sid`、`data_ticket`等会话级cookie过期后编辑器页面被重定向到登录页。

## Playwright Chromium版本问题

Hermes venv (playwright 1.58.0) 期望 `chromium-1208`，实际缓存有 `chromium-1217`：
```bash
ln -sf ~/.cache/ms-playwright/chromium-1217 ~/.cache/ms-playwright/chromium-1208
```

但Ubuntu Wayland上ms-playwright chromium无法加载微信页面（超时），需用 `channel='chromium'`。

## Integration

publish_draft.py 降级链（更新后）：
```
1. REST API access_token → 40164 →
2. Cookie浏览器自动化 (browser_publish.py, popup模式) →
3. 本地HTML保存 (手动粘贴)
```

旧 `cookie_publish.py`（operate_appmsg直连）→ **已停用**。

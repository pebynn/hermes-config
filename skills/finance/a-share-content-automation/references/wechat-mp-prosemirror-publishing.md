# 微信公众号 ProseMirror 编辑器 → 浏览器自动化发布

2026年微信后台编辑器重大升级：从旧版 UEditor+iframe 改为 **ProseMirror** 富文本编辑器 (DIV.contenteditable)。

## 与旧版的关键差异

| 项目 | 旧版 (UEditor) | 新版 (ProseMirror, 2026) |
|:--|:--|:--|
| 编辑器容器 | `<iframe id="ueditor_0">` | `<div class="ProseMirror">` |
| HTML源码模式 | `Ctrl+Shift+H` → textarea | **不存在** |
| 标题 | `input#title` | `textarea#title` |
| 保存按钮 | 工具栏按钮 | `#js_submit` ("保存为草稿") |
| Cookie API | `cgi-bin/operate_appmsg` 可用 | **已失效** (ret=2/200002) |

## 浏览器自动化完整流程

```python
from playwright.sync_api import sync_playwright

cookies = load_cookies()  # 14项完整cookie集

browser = p.chromium.launch(channel='chromium', headless=False, args=['--no-sandbox'])
context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="zh-CN")
context.add_cookies(cookies)
page = context.new_page()

# 1. 登录首页
page.goto("https://mp.weixin.qq.com/", timeout=60000)
time.sleep(4)
assert "cgi-bin/home" in page.url

# 2. 打开编辑器 (popup新标签页!)
page.get_by_text("新的创作").first.click()
time.sleep(2)
with context.expect_page(timeout=30000) as popup_info:
    page.get_by_text("文章", exact=True).first.click()

editor = popup_info.value
editor.wait_for_load_state("domcontentloaded")
time.sleep(5)

# 3. 填标题
editor.wait_for_selector("#title", timeout=10000)
editor.fill("#title", title)

# 4. 填正文 — ProseMirror JS注入
editor.evaluate(f"""
    var pm = document.querySelector('.ProseMirror');
    pm.innerHTML = {json.dumps(html_content)};
    pm.focus();
    pm.dispatchEvent(new Event('input', {{ bubbles: true }}));
""")

# 5. 保存草稿
editor.locator("#js_submit").click()
time.sleep(8)
```

## Cookie规范

必须从Chrome DevTools **全量导出**14项cookie，非仅 `poc_sid`:

```
bizuin, data_bizuin, data_ticket, mm_lang, rand_info,
slave_bizuin, slave_sid, slave_user, ua_id, uuid, wxuin, xid,
_clck, _clsk
```

存储路径: `~/.hermes/credentials/wechat_cookies.json`

## 图片方案

API上传需IP白名单，改用 **base64 data URI** 内嵌:

```python
import base64
img_bytes = Path("chart.png").read_bytes()
b64 = base64.b64encode(img_bytes).decode()
img_tag = f'<img src="data:image/png;base64,{b64}" style="max-width:100%"/>'
```

限制: 单张 <800KB (微信编辑器上限1MB)。

## 已知问题

- **"未授权使用切换账号"弹窗**: 非阻塞，不影响保存。扫码时未勾选"允许切换登录"导致。
- **浏览器选择**: Ubuntu Wayland 必须用 `channel='chromium'`(snap chromium)。ms-playwright chromium 无法加载mp.weixin.qq.com (页面超时)。
- **SingletonLock**: `launch_persistent_context` 使用同一user_data_dir时，前次残留的SingletonLock会导致启动失败。需清理或使用 `launch()` + `new_context()`。
- **Cookie有效期**: 约7-14天，过期后需从浏览器重新导出。

## 踩坑记录

1. ❌ `Ctrl+Shift+H` textarea → 新版只有 `#description`(摘要) textarea，不是内容区
2. ❌ 直接URL导航 `cgi-bin/appmsg?action=edit` → 被重定向到 loginpage
3. ✅ 从首页 "新的创作" → "文章" 触发 → 编辑器正确以popup打开
4. ❌ `ProseMirror.pmViewDesc.node.view` → 不可访问，`innerHTML` 注入可用
5. ❌ 页面抓取 `cgi-bin/appmsg?action=list_card` → 返回非JSON (cookie鉴权不覆盖此端点)
6. ❌ 仅 `poc_sid` cookie → 首页可登但编辑器重定向

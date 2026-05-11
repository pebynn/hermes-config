# WeChat MP ProseMirror 编辑器 — Playwright 注入完整方案

**最后更新**: 2026-05-08 | 实测环境: Ubuntu 24.04 Wayland, Playwright 1.58.0, snap chromium 147

## 编辑器架构变迁

| 时期 | 编辑器 | 正文注入方式 |
|:--|:--|:--|
| ~2024 | UEditor (`iframe#ueditor_0`) | `frame_locator` → `body.fill()` |
| 2025 | 过渡期 | Ctrl+Shift+H → textarea |
| 2026 | ProseMirror (`DIV.ProseMirror`) | `page.evaluate()` JS注入 |

## DOM 关键元素

| 元素 | 选择器 | 类型 | 填充方式 |
|:--|:--|:--|:--|
| 标题 | `#title` | TEXTAREA | `editor.fill('#title', title)` |
| 正文 | `.ProseMirror` | DIV contenteditable | JS innerHTML 注入 |
| 保存为草稿 | `#js_submit` | SPAN/btn | `editor.locator('#js_submit').click()` |
| 发表 | `#js_send` | SPAN/btn | - |
| 摘要 | `#js_description` | TEXTAREA | 可选 |
| 自动保存 | `#js_autosave` | SPAN | 系统自动 |

## 正文注入 (唯一可靠方式)

```python
import json

editor.evaluate(f"""
    var pm = document.querySelector('.ProseMirror');
    if (!pm) throw new Error('ProseMirror element not found');
    pm.innerHTML = {json.dumps(html_content, ensure_ascii=False)};
    pm.focus();
    pm.dispatchEvent(new Event('input', {{ bubbles: true }}));
""")
```

## 标题/正文分离铁律

页面仅有2个textarea:
1. `#title` — 标题
2. `#js_description` — 摘要

**没有任何内容textarea**。使用 `editor.wait_for_selector('textarea')` 会匹配 `#title`，导致正文灌入标题框。

## 编辑器Popup模式

点击"文章"后编辑器在新标签页打开:

```python
page.get_by_text("新的创作").first.click()
time.sleep(2)

with context.expect_page() as popup_info:
    page.get_by_text("文章", exact=True).first.click()

editor = popup_info.value
editor.wait_for_load_state("domcontentloaded")
time.sleep(5)
```

## HTML模式已死

`Ctrl+Shift+H` 在新版不产生textarea。已验证无效。

## 图片注入: base64 data URI

由于微信素材库API需要IP白名单，浏览器自动化无法使用CDN上传。
替代方案：图片以base64 data URI内嵌到HTML中。

```python
import base64
b64 = base64.b64encode(Path('chart.png').read_bytes()).decode()
img_tag = f'<img src="data:image/png;base64,{b64}" style="max-width:100%"/>'
```

注意：微信草稿箱正文上限约1MB，单张图建议<200KB。

## Cookie注入 (免扫码)

```python
cookies = json.loads(Path('wechat_cookies.json').read_text())
context = browser.new_context(viewport={"width":1280,"height":800}, locale="zh-CN")
context.add_cookies(cookies)
# 之后所有页面自动鉴权
```

必需cookie: `poc_sid`, `data_bizuin`, `data_ticket`, `slave_sid`, `slave_user`, `bizuin`, `ua_id`, `uuid`, `wxuin`, `xid` (~14项全量)

## 保存确认

保存后弹窗"未授权使用切换账号能力"是**非阻塞警告**，不影响草稿保存。

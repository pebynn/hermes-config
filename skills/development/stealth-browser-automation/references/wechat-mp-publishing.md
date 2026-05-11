# WeChat MP (微信公众号) 浏览器自动化发布 — Ubuntu Wayland 实测 (2026-05-08)

## Popup模式（编辑器在新标签页打开）

**关键发现**：点击"文章"后编辑器在popup新标签页打开，不是同页跳转。

```python
page.goto("https://mp.weixin.qq.com/")
page.get_by_text("新的创作").first.click()
time.sleep(2)

with context.expect_page() as popup_info:
    page.get_by_text("文章", exact=True).first.click()

editor = popup_info.value
# 后续操作针对editor页面
```

## DOM结构（2026-05-08 实测）

| 元素 | 选择器/类型 | 填充方式 | 备注 |
|:--|:--|:--|:--|
| 标题 | `TEXTAREA#title` | `editor.fill('#title', title)` ✅ | 不是INPUT |
| 正文 | `DIV.ProseMirror` | JS `innerHTML` 注入 + `input` event | **不是iframe，无HTML mode textarea** |
| 保存为草稿 | `#js_submit` | `editor.locator('#js_submit').click()` | 文本="保存为草稿" |
| 摘要 | `TEXTAREA#js_description` | - | 不填则自动抓正文 |

## 正文注入（ProseMirror — 核心）

**Ctrl+Shift+H 无效**：新编辑器不再生成内容textarea。必须直接操作ProseMirror DOM：

```python
editor.evaluate(f"""
    var pm = document.querySelector('.ProseMirror');
    if (!pm) throw new Error('ProseMirror element not found');
    pm.innerHTML = {json.dumps(html_content, ensure_ascii=False)};
    pm.focus();
    pm.dispatchEvent(new Event('input', {{ bubbles: true }}));
""")
```

**为什么不能用 textarea.fill()**：
- 页面有2个textarea: `#title`(标题) + `#js_description`(摘要)
- 没有任何内容textarea — `editor.wait_for_selector('textarea')` 会匹配到 `#title`
- 导致正文被灌入标题框 → 标题过长报错

## 保存操作

```python
editor.locator("#js_submit").click()  # text="保存为草稿"
time.sleep(5)
```

保存后弹窗"未授权使用切换账号能力"是**非阻塞警告**，不影响草稿保存。

## Ubuntu Wayland 配置

```python
browser = p.chromium.launch(
    channel='chromium',  # 必须！ms-playwright chromium 超时
    headless=False,
    args=['--no-sandbox'],
)
```

**ms-playwright chromium问题**：Ubuntu 24.04 Wayland环境下所有页面导航超时(30000ms)，`channel='chromium'`使用snap chromium可正常加载。

## Cookie注入（免反复扫码）

```python
cookies = json.loads(Path("wechat_cookies.json").read_text())
context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="zh-CN")
context.add_cookies(cookies)
page = context.new_page()
page.goto("https://mp.weixin.qq.com/")  # 自动跳cgi-bin/home → 已登录
```

**完整cookie清单（14项）**：`_clck`, `_clsk`, `bizuin`, `data_bizuin`, `data_ticket`, `mm_lang`, `rand_info`, `slave_bizuin`, `slave_sid`, `slave_user`, `ua_id`, `uuid`, `wxuin`, `xid`

**有效期**：数天到一周。过期后从Chrome DevTools重新导出。

## 已废弃方式

| 方式 | 原因 |
|:--|:--|
| `cgi-bin/operate_appmsg` Cookie API | 返回 `ret=2`(列表查询) / `ret=200002`(参数错误)，不可创建 |
| `Ctrl+Shift+H` 切换HTML模式 | 新版编辑器不生成内容textarea |
| `editor.fill('textarea', content)` | textarea选择器匹配到 `#title` 而非内容区 |
| 直接 `editor.goto(editor_url)` | 编辑器检测非浏览器环境，重定向到loginpage |
| `iframe#ueditor_0` 填充 | 编辑器已从UE迁移到ProseMirror |

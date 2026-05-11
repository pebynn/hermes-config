# PDD 商家后台登录实现模式

目标 URL: `https://mms.pinduoduo.com/login/`
首页 URL: `https://mms.pinduoduo.com/home/`

## 页面结构特点

- React SPA, 渲染有延迟 (login → 约 2s)
- 默认显示扫码登录, 需要切换到"账号登录" Tab
- 输入框 ID: `#usernameId`, `#passwordId`
- 登录按钮: 文本包含"登录"
- 登录成功: 跳转到 `/home/`
- 关键 Cookie 名: `MMS_SESS`, `MMS_UIN`, `PASS_ID`, `session_id`

## Tab 切换策略

拼多多商家后台默认展示扫码登录界面。切换到账号密码表单可以通过多种方式:

1. 精确文字匹配: `page.get_by_text("账号登录", exact=True)`
2. CSS 选择器回退: `.login-tab-account`, `[data-tab="account"]`
3. 遍历文本含"账号"/"密码"的可见按钮/链接

建议按优先顺序尝试, 因为 SPA 的 class 名称可能随版本变化。

## 滑块验证码检测

登录过程中可能出现滑块验证码。检测特征:

```python
captcha_selectors = [
    'div[id*="captcha"]',
    'div[class*="captcha"]',
    'div[class*="slider"]',
    'div[class*="validate"]',
    'canvas[class*="captcha"]',
]
```

检测到后, 脚本应轮询等待用户手动完成, 最多等 60 秒。

## Cookie 恢复验证

检查会话有效性的方法:

1. fetch `HOME_URL` 看是否跳转到 `/home/` (而非返回到 `/login/`)
2. 检查 context cookies 中是否存在 `MMS_SESS` 或 `PASS_ID`
3. 检查页面中是否出现 `.user-avatar` 等已登录特征元素

## 参考脚本

输出位置: `~/PDD/pdd_login.py`

核心结构:

```python
from scrapling.fetchers import StealthySession

def build_page_action(username, password):
    def action(page):
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        _switch_to_account_tab(page)
        _fill_login_form(page, username, password)
        _click_login_button(page)
    return action

with StealthySession(
    headless=False,
    user_data_dir="~/.pdd_browser_profile",
    page_action=build_page_action("user", "pass"),
    hide_canvas=True,
    block_webrtc=True,
    solve_cloudflare=True,
    real_chrome=True,
) as session:
    session.fetch(LOGIN_URL)
    time.sleep(3)
    cookies = session.context.cookies()
    # 验证登录状态
```

## 已知坑

- PDD 对 headless Chrome 有检测, 必须用 `real_chrome=True`
- 初次登录后可能需要手动关闭浏览器窗口 (StealthySession 的 context manager 会自动关闭)
- `user_data_dir` 路径不要含空格/中文

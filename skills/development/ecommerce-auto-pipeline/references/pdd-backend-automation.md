# PDD 商家后台自动化 — 技术文档

> 创建日期: 2026-05-01
> 关联脚本: ~/PDD/pdd_login.py
> 可行性报告: ~/pdd_mms_playwright_feasibility.md

## 背景与选型

拼多多商家后台（mms.pinduoduo.com）提供商品管理、订单处理、售后、数据看板等功能。对接路径有三条：

| 路径 | 可行性 | 结论 |
|:--|:--|:--|
| 开放平台商家 API | 需企业资质审核 T+3工作日 | 门槛高，但长期最稳定 |
| 多多进宝 API | 注册即拿 key，但只能做推广/商品查询 | 不能操作店铺，辅助用 |
| 浏览器自动化 | 零门槛，Playwright/scrapling | **当前最优选** |

## scrapling 核心能力

### StealthySession — 会话持久化

```python
from scrapling.fetchers import StealthySession

session = StealthySession(
    headless=False,                          # 首次登录需可视化
    user_data_dir='~/.pdd_browser_profile',  # 浏览器 profile 持久化
    solve_cloudflare=True,                   # 自动处理 Turnstile
    hide_canvas=True,                        # 反 Canvas 指纹
    block_webrtc=True,                       # 防 WebRTC 泄露
    real_chrome=True,                        # 减少 headless 检测
)
```

`user_data_dir` 是关键 — 浏览器 profile（含 Cookie、LocalStorage、SessionStorage）全部持久化到磁盘。第一次登录后，后续启动直接复用，无需重新登录。

### page_action 钩子

`page_action` 接收 Playwright Page 对象，可执行任意浏览器操作：

```python
def login_action(page: Page):
    # 1. 切换到账号密码登录
    page.click('text=账号登录')  # 或密码登录 Tab
    
    # 2. 填入凭据
    page.fill('#usernameId', username)
    page.fill('#passwordId', password)
    
    # 3. 点击登录
    page.click('button:has-text("登录")')
    
    # 4. 检测滑块验证码
    try:
        page.wait_for_selector('.captcha', timeout=3000)
        input('>>> 检测到滑块验证码，请手动完成，完成后按 Enter...')
    except:
        pass  # 无验证码，正常流程

page = session.fetch(
    'https://mms.pinduoduo.com/login/',
    page_action=login_action,
    wait_until='networkidle'
)
```

## PDD 商家后台页面结构

### 登录页 (mms.pinduoduo.com/login/)
- React 16 SPA
- 默认显示扫码登录（二维码）
- 需点击 Tab 切换到「账号登录/密码登录」
- 输入框: `#usernameId`, `#passwordId`
- 登录按钮: `<button>` 内含文本「登录」
- 反爬: 滑块验证码（Turnstile 或自研）
- 180 个 DOM 元素，readyState: complete

### 登录成功特征
- URL 从 `/login/` 跳转到 `/home/` 或其他业务页面
- 或页面中出现商家后台导航元素

## 已验证的页面元素（2026-05-01）

| 元素 | 选择器 | 状态 |
|:--|:--|:--|
| 用户名输入框 | `#usernameId` | 稳定 |
| 密码输入框 | `#passwordId` | 稳定 |
| 登录按钮 | `button:has-text("登录")` | 待验证 |
| 账号登录 Tab | `text=账号登录` | 待验证 |
| 滑块验证码 | `.captcha` | 存在但选择器待确认 |

## 依赖

- scrapling >= 0.4.7 (`pip install scrapling[all]`)
- Playwright 1.58（scrapling 底层引擎）
- Python 3.12+
- Chromium 浏览器

## 已知问题

1. **lxml 版本冲突**: scrapling 需 lxml>=6.0.3，crawl4ai 需 lxml~=5.3。当前已安装 6.1.0，crawl4ai 可能受影响。
2. **headless 检测**: 拼多多可能对 headless 浏览器有额外检测，首次登录建议 `headless=False`。
3. **滑块验证码**: `solve_cloudflare=True` 对拼多多自研滑块效果待验证，目前策略是暂停等待手动完成。

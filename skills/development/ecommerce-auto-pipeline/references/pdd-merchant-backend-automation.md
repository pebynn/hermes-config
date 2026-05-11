# PDD 商家后台浏览器自动化

> 补充于 2026-05-01，配合 `ecommerce-auto-pipeline` 使用。
> 对标脚本: `~/PDD/pdd_login_v2.py`

## 背景

拼多多商家后台 (mms.pinduoduo.com) 没有公开的商家操作 API（上架/改价/发货等）。两条路线：

| 方案 | 适用场景 | 难度 |
|:--|:--|:--|
| **多多进宝 API** (jinbao.pinduoduo.com) | 商品搜索、推广链接、佣金查询 | 低 — 注册即拿 client_id |
| **浏览器自动化** (Playwright) | 上架、发货、改价、运营数据拉取 | 中 — 需处理滑块验证码 |
| **开放平台商家后台系统** | 订单/商品管理（需企业资质审核，T+3工作日） | 高 |

## 已验证可用的登录流程

```
打开 mms.pinduoduo.com/login/
  → 页面是 React 16 SPA，默认扫码登录
  → 切到"账号登录" Tab（text=账号登录）
  → 填 #usernameId / #passwordId
  → 点登录按钮（button:has-text("登录")）
  → [滑块验证码] ← 当前瓶颈
  → 首页跳转 → 保存 storage_state
```

## Stealth 配置（绕过自动化检测）

```python
# launch args
browser = p.chromium.launch(headless=True, args=[
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox'
])

# JS 注入
page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = {runtime: {}};
    Object.defineProperty(navigator, 'permissions', {
        get: () => ({query: () => Promise.resolve({state: 'prompt'})})
    });
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
""")
```

## 已知陷阱

### 1. 弹窗遮挡 (MDL_container modal)
PDD 可能弹出协议弹窗遮挡 Tab 切换按钮。使用 `page.keyboard.press('Escape')` 尝试关闭。或使用 `el.click(force=True)` 绕过拦截检查。

### 2. 滑块验证码 (缺口匹配型)
- 检测到轨道宽度 ~411px，滑块按钮在区域内
- 这是图片缺口匹配型滑块，headless 环境下缺乏 CV 库无法精确计算拖拽距离
- 盲试 8+ 种距离全部失败
- **可行方案**: 
  a. 接入 2captcha/trucaptcha 等验证码求解 API（~0.01元/次）
  b. 用 headful 模式手动过一次滑块，保存 auth 文件后永久复用
  c. 短信验证码登录作为备选

### 3. scrapling/patchright EPIPE (Node.js v24)
scrapling 的 StealthySession 底层用 patchright，在 Node.js v24.13+ 下 EPIPE 崩溃。改用原生 Playwright。

### 4. lxml 版本冲突
scrapling[all] 要求 lxml>=6.0，可能与 crawl4ai (需要 ~5.3) 冲突。当前系统已降级处理。

## 会话持久化

```python
# 保存
context.storage_state(path="~/.pdd_auth.json")

# 恢复
context = browser.new_context(storage_state="~/.pdd_auth.json")
```

## 下一步可自动化操作（P1-P2）

| 优先级 | 操作 | 依赖 |
|:--|:--|:--|
| P1 | 商品发布（对接 prepare_listing 管线） | 登录态 |
| P1 | 批量发货 | 登录态 + 订单列表 |
| P2 | 运营数据拉取（订单/售后/DSR） | 登录态 |
| P2 | 商品编辑/下架 | 登录态 |

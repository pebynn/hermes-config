# Xueqiu (xueqiu.com) 反自动化检测深度分析

> 调研时间: 2026-05-07
> 平台: 雪球 (xueqiu.com) — 中国最大投资者社区

## 结论摘要

雪球 React 前端具有**多层反自动化检测**，即使使用有效 Cookie 和 Playwright headless/headful 模式，发布按钮的点击事件仍被拦截。API 直接调用同样被 WAF 阻断（阿里云 WAF 400019）。**全自动发布不可行**，建议降级为本地备份 + 人工发布。

## 检测层次

### 层次 1: 阿里云 WAF（API 层）

- 所有 `/statuses/*` 和 `/article/*` 端点被 WAF 保护
- 直接 POST 返回 `400019` 错误码: "遇到错误，请刷新页面后重试"
- 返回 WAF challenge token (`_waf_bd8ce2ce37`)
- 股票行情 API (`/v4/stock/quote.json`) 不受 WAF 保护，可用于 Cookie 验证

### 层次 2: Cookie 多因子认证（Web 层）

雪球 Web 登录态要求**完整 Cookie 集合**，单一 token 不够：

**必须的 Cookie:**
- `xq_a_token` — 访问令牌 (40 字符 hex)
- `xq_r_token` — 刷新令牌 (40 字符 hex，配对使用)
- `xq_id_token` — JWT 身份令牌 (含用户 uid)
- `xq_is_login` — 登录状态标记 (值必须为 "1")
- `u` — 用户 ID

**辅助 Cookie（可能也需要）:**
- `acw_tc` — 阿里云 WAF 通行令牌
- `ssxmod_itna` / `ssxmod_itna2` — 雪球自研反爬令牌
- `smidV2` — 设备标识
- `cookiesu` — 用户 Cookie 标识
- `device_id` — 设备指纹
- `remember` — 记住登录标记

**获取方式:** 浏览器登录后从 DevTools → Application → Cookies 导出**全部** cookies（不是只导 xq_a_token）

### 层次 3: React 事件拦截（前端层）

即使 Cookie 完整、页面显示"已登录"且编辑器可见，点击发布按钮 (`button.submit__confirm__btn`) 仍不触发提交：

**测试过的方案（全部失败）:**
- `el.click()` — Playwright 标准点击
- `el.click(force=True)` — 强制点击
- `page.mouse.click(x, y)` — 坐标点击
- `el.evaluate('el => el.click()')` — JS 原生点击
- `el.dispatchEvent(new MouseEvent('click'))` — 事件模拟
- `page.keyboard.press('Control+Enter')` — 快捷键

**推测原因:**
1. React 合成事件系统检测非人工触发（`isTrusted: false`）
2. `navigator.webdriver` 属性被检测
3. 按钮的 `onClick` 被 React HOC 包装，需要额外的前置条件
4. 可能需要在编辑器内触发真实的 `input` 事件（`textContent` 赋值不触发 onChange）

## 有效的替代方案

### Cookie 验证（可行）

使用公开的股票行情 API 验证 Cookie 有效性：

```python
VERIFY_URL = "https://xueqiu.com/v4/stock/quote.json?code=SH000001"
# 返回真实股价数据 → Cookie 有效
# 返回空/错误 → Cookie 失效
```

### 本地备份 + 人工发布（推荐）

```python
# 1. Cookie 验证通过
# 2. 保存 Markdown 备份到 ~/writing-data/xueqiu-backups/
# 3. 打印手动发布指引
# 4. cron 运行不报错，优雅降级
```

### 编辑器内容填充（已确认可行）

编辑器 DOM 结构：
- 标题区域：雪球编辑器第一行即为标题，无独立 title input
- 编辑器：`div.medium-editor-element`（MediumEditor 库）
- 激活方式：需先点击"写长文" tab（`page.locator('text=写长文').first.click()`）
- Visibility：需等待 React hydration（`wait_for_selector(state='visible')`）
- 内容填充：`el.evaluate("(el, text) => { el.textContent = text; }", content)` 可行

### 登录态持续时间

- Cookie 有效期: 约 7-30 天
- 刷新需要: 浏览器重新登录 → 导出全部 cookies → 更新 JSON 文件

## 相关教训

- `networkidle` 在雪球页面会永久超时（长期 WebSocket 连接）
- 使用 `wait_until='load'` 替代，配合 `page.wait_for_timeout(5000)` 等待 SPA 渲染
- 不要使用 `navigator.clipboard.writeText()` — 雪球页面可能拦截 clipboard API

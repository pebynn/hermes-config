# PDD商家后台自动化方案

> 2026-05-01 技术验证产出。ec-domain 发布层（pdd_listing）的落地实现参考。

## 方案对比

| 方案 | 门槛 | 能做什么 | 不能做什么 |
|:--|:--|:--|:--|
| 多多进宝 API | 最低，注册即拿 key | 商品搜索、推广链接、佣金查询 | 不能上架/发货/改价 |
| Playwright 浏览器自动化 | 有商家账号即可 | 全部商家后台操作 | 页面改版需维护 |
| 商家开放平台 API | 需企业资质+审核 | 完整API能力 | 审核周期长 |
| 三方ERP（聚水潭等） | 中等 | 间接操作拼多多 | 多一层依赖，部分收费 |

## 推荐路径

**主力：Playwright + Scrapling 浏览器自动化**（零门槛，立即可用）
**备胎：多多进宝 API**（顺手注册，能用则用）

## Playwright 自动化验证结果

- 商家后台地址：https://mms.pinduoduo.com/ （自动跳转 /login/）
- 技术栈：React 16 SPA
- 元素定位：`#usernameId` / `#passwordId` 稳定可用
- 默认扫码登录，需先切到账号密码 Tab
- 存在滑块验证码

## Scrapling 加持

Scrapling 的 StealthySession 直接覆盖 P0 需求：
- Cookie 持久化 → 内置会话管理
- 反指纹 → hide_canvas + block_webrtc
- Cloudflare Turnstile → solve_cloudflare=True
- page_action 钩子 → 复用现有 Playwright 经验

```bash
pip install "scrapling[all]"
scrapling install
```

## Cookie 持久化策略（P0）

```
首次：手动扫码登录 → 导出 Cookie JSON → 存本地
后续：加载 Cookie → page.goto() → 检测登录态 → 过期则通知用户重扫
```

关键点：拼多多 session 有效期通常 1-2 小时，需定期刷新。

## 自动化优先级

| 优先级 | 模块 | 说明 |
|:--|:--|:--|
| P0 | Cookie持久化 + Stealth | 所有后续自动化的前提 |
| P1 | 商品发布/编辑 | 对接 prepare_listing → listing.json |
| P2 | 订单处理 | 批量发货、售后处理 |
| P3 | 运营数据 | 销售报表、DSR监控、库存预警 |

完整可行性报告：~/pdd_mms_playwright_feasibility.md

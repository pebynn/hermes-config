# PDD商家后台前端内部API反抓取笔记 (janus网关)

> 研究日期: 2026-05-04
> 方法: Playwright + CDP Network拦截 (headless)
> 完整捕获数据: `~/research-skill-graph/projects/pdd-full-automation-feasibility/captured_api_headless.json` (290KB, 119请求+109响应)
> 分析报告: `~/research-skill-graph/projects/pdd-full-automation-feasibility/pdd-frontend-api-analysis.md`

## 两套API体系对比

| 特性 | 开放平台API (gw-api) | 前端内部API (janus网关) |
|------|---------------------|----------------------|
| 网关 | `gw-api.pinduoduo.com/api/router` | `mms.pinduoduo.com/janus/api/*` |
| 认证 | OAuth 2.0 + MD5签名 | Cookie (PASS_ID) + Anti-Content签名 |
| 文档 | 官方文档完善 | 无公开文档, 需抓包 |
| 商品发布接口 | `pdd.goods.add` (需ISV企业审核) | 未知 (已捕获登录层, 发布层需登录后抓) |
| 个人可用 | ❌ 需企业资质 | ⚠️ 有Cookie即可, 但Anti-Content需JS计算 |

## 已发现的janus端点

| 端点 | 方法 | 功能 | 认证要求 |
|------|------|------|---------|
| `/janus/api/new/userinfo` | POST | 用户信息查询 | Cookie (未登录返回`uid: -1`) |
| `/janus/api/scan/login/qrcode` | POST | 生成二维码登录ticket | 无 |
| `/janus/api/scan/login/query` | POST | 轮询扫码状态 | 无 |
| `/janus/api/queryPasswordEncrypt` | GET | 密码加密公钥 | 无 |
| `/earth/api/pack/queryPackList` | POST | 查询打包列表 | Cookie |
| `/merchant-web-service/leonWithoutLogin` | POST | 匿名服务(leon) | 无 |
| `api.pinduoduo.com/api/server/_stm` | GET | 时间戳/服务器时间 | 无 |
| `apm.pinduoduo.com/api/pmm/*` | POST | APM埋点/日志 | 无 |

## Anti-Content签名机制 (关键阻塞)

所有请求头携带 `anti-content` 字段, 长字符串(~256 chars):

```
anti-content: 0apWtxUkM_Venx7g0-NGNJ4TLQF1G0ep-N6lrAeHq9YXLvyPbUyFolYiETqyYTYiQ8Xv-nq5jGdpyGXuMY25-...
```

从CORS响应头确认:

```
access-control-allow-headers: Origin, X-Requested-With, Content-Type, ..., AccessToken, PASSID, VerifyAuthToken, Anti-Content
```

**这意味着:**
- janus API设计上支持直接HTTP调用（不依赖浏览器DOM）
- 但需要前端JS计算 `anti-content` 签名
- 签名算法在打包后的JS中, 需逆向
- 已知 `leonWithoutLogin` 请求的body: `{"type": "dab9cced68c34e979108ed270776bdbd"}` (固定type)

## 认证流程

```
商家后台页面 → 检查cookie → 检查PASS_ID有效期
    ↓ (有效)          ↓ (无效)
  载入页面     →  重定向到 /login/
                  ↓
              生成QR ticket → 手机扫码
                  ↓
              写入PASS_ID + JSESSIONID
                  ↓
              重定向回原页面
```

## Cookie审计 (2026-05-04 捕获)

| Cookie名 | 域 | 有效期 | 关键性 |
|----------|-----|--------|-------|
| PASS_ID | mms.pinduoduo.com | ~10天 | ❗核心认证 |
| JSESSIONID | mms.pinduoduo.com | 会话级 | 需刷新 |
| windows_app_shop_token_23 | .pinduoduo.com | ~6.5h | JWT格式 |
| _nano_fp | mms.pinduoduo.com | ~400天 | 浏览器指纹可复用 |
| api_uid | .pinduoduo.com | ~400天 | 设备标识 |

## 捕获方法 (Playwright)

```python
from playwright.sync_api import sync_playwright

# headless模式 + slow_mo=50可缓解Node v24 EPIPE
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, slow_mo=50)
    context = browser.new_context(storage_state="~/.pdd_auth.json")
    page = context.new_page()
    
    # 拦截请求
    page.on("request", lambda r: capture(r))
    page.on("response", lambda r: capture(r))
    
    page.goto("https://mms.pinduoduo.com")
    # 保存新auth
    context.storage_state(path="~/.pdd_auth_fresh.json")
```

## 已知限制

| 限制 | 说明 |
|:----|:-----|
| Node.js v24 EPIPE | headed模式容易触发, headless+slow_mo可缓解 |
| 登录态过期 | ~/.pdd_auth.json 的 JSESSIONID 每小时左右过期 |
| Anti-Content签名 | 需逆向JS, 否则无法直接curl调用 |
| 商品发布API未捕获 | 需要登录态才能导航到发布页, 捕获提交时的XHR |

## 推荐后续方向

1. **用户手动开Chrome + DevTools** — 最可靠方式, 登录后走一遍发布流程, 抓XHR
2. **JS逆向Anti-Content算法** — 在minified JS中找签名生成函数
3. **Cookie保活** — 用Playwright headless每10分钟访问一次后台保活PASS_ID

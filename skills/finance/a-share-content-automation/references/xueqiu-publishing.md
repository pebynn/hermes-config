# 雪球长文发布技术文档

> 最后更新：2026-05-07

## 发布方式

### API方案（已废弃）
- 端点 `https://xueqiu.com/statuses/update.json` 返回 400019 错误
- 其他尝试过的端点：`/article/publish`(404)、`/statuses/article.json`(404)、`/cubes/create.json`(400)
- **结论**：雪球后端变更API，纯requests方案不可行

### 浏览器自动化方案（半可行）
- 使用 Playwright 模拟用户行为：导航到 `/write` → 点击"写长文"tab → 填写正文 → 点击发布
- 编辑器：MediumEditor (class=`medium-editor-element`)，需 `wait_for_selector(state='visible')` 等 React hydration
- 标题：雪球编辑器第一行即为标题（无独立 title input）
- **⚠️ 致命限制**：雪球 React 前端拦截所有合成点击事件。即使 Cookie 完整、页面显示"已登录"、编辑器可见且内容已填入，`.submit__confirm__btn` 按钮的点击（含 `el.click()`、`page.mouse.click()`、`el.dispatchEvent()`、`el.evaluate('el => el.click()')`）全部不触发提交。**全自动发布不可行。**

### 降级方案（当前生效）
publish_to_xueqiu.py 自动降级：
1. Cookie 验证（通过 `/v4/stock/quote.json`）→ 确认登录态
2. 保存 Markdown 备份到 `~/writing-data/xueqiu-backups/`
3. 写入发布日志到 `~/writing-data/publish-logs/YYYY-MM-DD-xueqiu.log`
4. 打印手动发布指引（URL + 标题 + 文件路径）
5. Cron 运行不报错，优雅退出

## Cookie要求（关键！）

### 必须的 Cookie（缺一不可）
| Cookie | 用途 | 类型 |
|:--|:--|:--|
| `xq_a_token` | 访问令牌（40字符hex） | HttpOnly |
| `xq_r_token` | 刷新令牌（40字符hex） | HttpOnly |
| `xq_id_token` | JWT身份令牌（含用户uid） | HttpOnly |
| `xq_is_login` | 登录状态标记（值="1"） | — |
| `u` | 用户ID | — |

### 辅助 Cookie（可能也需要）
`acw_tc`（阿里云WAF）、`ssxmod_itna`/`ssxmod_itna2`（雪球反爬）、`smidV2`（设备标识）、`cookiesu`、`device_id`、`remember`

### 获取方式
浏览器登录雪球 → F12 → Application → Cookies → xueqiu.com → **导出全部cookies** → 保存到 `~/.hermes/credentials/xueqiu_cookies.json`

### Cookie验证
使用 `/v4/stock/quote.json?code=SH000001` 端点。有效cookie返回股票数据（含`name`和`current`字段）。**不要用 `/setting/user`**——其HTML源码含"login"字样（JS变量），会被误判为需要登录。

## WAF 防护

雪球使用阿里云WAF保护所有写操作端点。请求返回 `_waf_bd8ce2ce37` challenge token。Playwright 浏览器可自动通过WAF，但发布按钮的React事件拦截是独立于WAF的另一层防护。

## Cron

| ID | 名称 | 时间 | 
|:---|:-----|:-----|
| `18619f5cdf16` | 雪球每日复盘发布 | `30 16 * * 1-5` |

微信发布后30分钟触发，给予人工审核窗口。

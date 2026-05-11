# 微信公众平台浏览器自动化发布 — 已验证方案 (2026-05-08)

## 工作原理

使用Playwright浏览器自动化 + Cookie鉴权，绕过开发者API的IP白名单限制。

**已废弃的方式**：
- `cgi-bin/operate_appmsg` Cookie直连API → 返回 `ret=2`(列表)/`ret=200002`(参数错误)
- `Ctrl+Shift+H` 切换HTML源码模式 → 新版编辑器不生成内容textarea

## 完整流程

```
Cookie加载 (14项, wechat_cookies.json)
  → Chromium启动 (channel='chromium', headless=False)
  → mp.weixin.qq.com 首页 (自动登录)
  → 点击"新的创作" → 点击"文章"
  → context.expect_page() 拦截编辑器popup新标签
  → editor.fill('#title', title)      — 标题textrea
  → editor.evaluate(ProseMirror注入)   — 正文DIV
  → editor.locator('#js_submit').click() — 保存为草稿
```

## 关键DOM选择器

| 元素 | 选择器 | 填充方式 |
|:--|:--|:--|
| 标题 | `TEXTAREA#title` | `fill()` ✅ |
| 正文 | `DIV.ProseMirror` | JS `innerHTML` + `input` event |
| 保存 | `#js_submit` | `click()` — "保存为草稿" |

## Cookie需求

必须14项完整cookie集:
`_clck`, `_clsk`, `bizuin`, `data_bizuin`, `data_ticket`, `mm_lang`, `rand_info`, `slave_bizuin`, `slave_sid`, `slave_user`, `ua_id`, `uuid`, `wxuin`, `xid`

仅 `poc_sid` 不够。

## 脚本

`~/writing-data/scripts/browser_publish.py` — 完整实现，已接入 `publish_draft.py` L3降级链

```bash
# 命令行
python3 browser_publish.py --date 2026-05-08 [--type daily|weekly]
python3 browser_publish.py --date 2026-05-08 --dry-run  # 仅验证
```

## 已知限制

- Cookie有效期: 数天至1周，过期后需从Chrome DevTools重新导出
- Ubuntu Wayland: 必须 `channel='chromium'` (snap chromium)，ms-playwright chromium 无法加载页面
- 保存后弹窗"未授权使用切换账号能力"为非阻塞警告

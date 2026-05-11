# 微信公众平台浏览器自动化发布 — 已验证方案 v1.1 (2026-05-08)

## 工作原理

Playwright浏览器自动化 + Cookie鉴权，绕过开发者API的IP白名单限制。

**已废弃的方式**：
- `cgi-bin/operate_appmsg` Cookie直连API → 返回 `ret=2`(列表)/`ret=200002`(参数错误)
- `Ctrl+Shift+H` 切换HTML源码模式 → 新版ProseMirror编辑器不生成内容textarea
- UEditor iframe (`#ueditor_0`) → 已迁移至ProseMirror

## 完整流程

```
Cookie加载 (14项, wechat_cookies.json)
  → Chromium (channel='chromium', headless=False)
  → mp.weixin.qq.com 首页 (Cookie自动登录)
  → 点击"新的创作" → 点击"文章"
  → context.expect_page() 拦截编辑器popup新标签
  → editor.fill('#title', title)          — 标题TEXTAREA
  → editor.evaluate(ProseMirror注入)       — 正文DIV
  → editor.locator('#js_submit').click()   — 保存为草稿
```

## 关键DOM

| 元素 | 选择器 | 填充方式 |
|:--|:--|:--|
| 标题 | `TEXTAREA#title` | `fill()` |
| 正文 | `DIV.ProseMirror` | JS `innerHTML` + 触发 `input` event |
| 保存 | `#js_submit` | `click()` — "保存为草稿" |

## 图片处理 (v1.1)

图片以 base64 data URI 内嵌到HTML正文中，按章节映射插入:

| 图表 | 插入章节 |
|:--|:--|
| kline.png | "大盘回顾" 标题后 |
| market_breadth.png | "技术看盘" 标题后 |
| sector_heatmap.png | "热点" 标题后 |
| capital_flow.png | "资金风向" 标题后 |

`md_to_html()` 函数自动处理: 提取图片→解析路径→base64编码→按章节关键字插入→去元数据→去图表列表。

## Cookie

必须14项完整cookie集:
`_clck`, `_clsk`, `bizuin`, `data_bizuin`, `data_ticket`, `mm_lang`, `rand_info`, `slave_bizuin`, `slave_sid`, `slave_user`, `ua_id`, `uuid`, `wxuin`, `xid`

仅 `poc_sid` 不够。Cookie有效期约数天至1周。

## 脚本

`~/writing-data/scripts/browser_publish.py`

```bash
python3 browser_publish.py --date 2026-05-08 --type daily
python3 browser_publish.py --date 2026-05-08 --dry-run
```

已接入 `publish_draft.py` L3降级链（venv python3, timeout 300s, 无--headless）。

## 环境要求

- Ubuntu Wayland: 必须 `channel='chromium'` (snap chromium)
- Playwright: `pip install playwright`
- Python venv: `~/.hermes/hermes-agent/venv/bin/python3`

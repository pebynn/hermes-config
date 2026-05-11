# ec-domain 数据管线布线检查 (2026-05-10)

## 接线现状

| 数据流 | 源 | 采集方式 | 自动化程度 | 状态 |
|--------|-----|---------|-----------|------|
| 选品关键词 | 淘宝/拼多多/抖音 | collect_hot_words.py | 手动 | 🟡 可运行 |
| 商品图片 | 17zwd.com | download_from_17zwd.py (Playwright) | 手动 | 🟡 需17网登录 |
| 上架准备 | 本地 | prepare_listing.py | 手动 | 🟡 可运行 |
| PDD发布 | mms.pinduoduo.com | pdd_listing_v3.py (Playwright) | 手动 | 🔴 全部失败 |
| 订单数据 | mms.pinduoduo.com | 手动录入 JSON | 手动 | 🟡 结构正确 |
| 退货数据 | mms.pinduoduo.com | 手动录入 JSON | 手动 | 🟡 结构正确 |
| 评价数据 | mms.pinduoduo.com | 手动录入 JSON | 手动 | 🟡 结构正确 |
| 库存数据 | mms.pinduoduo.com | 手动录入 JSON | 手动 | 🔴 12天过期 |
| 运营日报 | 本地数据汇总 | send_wechat_report.py | ❌ 无cron | 🟡 脚本就绪 |
| 差评回复 | 微信网关 | 无脚本 | ❌ | 🔴 0回复 |
| 活动报名 | mms.pinduoduo.com | 无脚本 | ❌ | 🔴 未启动 |

## 关键断点

### 断点1: PDD数据入口 (P0)
- **问题**: 订单/退货/评价/库存数据全部是手动录入 JSON 格式 (mock 数据)
- **来源**: 目录结构正确但数据时效差, 且无 PDD 商家后台 API/爬虫拉取
- **修复方案**: 需要 PDD API access_token 或 Playwright 从后台导出页抓取

### 断点2: 商品发布 (P0)
- **问题**: Playwright 因 React beast-core checkbox 阻塞 + pipe 模式不工作, 13款商品0款成功
- **阻塞根因**: `beast-core` 组件的 React SyntheticEvent 重写 + Wayland/Xwayland FD 传递问题
- **替代路径**: PDD API (需企业资质) → CSV批量导入 → 修补 Playwright pipe

### 断点3: 运营消息推送 (P1)
- **问题**: WeChat 发送脚本已写好 (5个版本) 但无 cron 自动触发
- **凭证**: token/chat_id/account_id 已配置
- **修复**: 添加 cron job `0 9 * * *` 执行 `python3 ~/PDD/运营/send_wechat_v2.py`

### 断点4: 活动联动 (P1)
- **问题**: pdd-activity-calendar skill 内容完善, 但无脚本检查活动版位/报名状态
- **当前时机**: 5月母亲节黄金窗口, 无商品报名

## 自动化优先级排序

| 优先级 | 动作 | 预估工时 | 前置条件 |
|--------|------|---------|---------|
| P0 | 处理28单待发货 | 2h | PDD商家后台登录 |
| P0 | 回复6条差评 | 1h | — |
| P1 | 处理12笔退货pending | 1h | PDD商家后台 |
| P1 | 添加cron: 运营日报推送 | 0.5h | WeChat凭证已就绪 |
| P1 | 添加cron: 每日选品建议 | 1h | 选品脚本就绪 |
| P2 | 修复Playwright pipe/改用API | 4h+ | 企业资质 |
| P2 | 重跑库存同步 | 1h | PDD商家后台 |

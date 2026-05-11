# Cron 调度优化记录 (2026-05-08)

## 问题

b60f3c86dd1b 信号扫描cron 21:00运行, 因扫描耗时30min+经常跑过午夜,
导致调度器跳过次日同一时段的run (spillover bug).

同时:
- policy_detect.py 13步网络下载~87min → 改跳过
- N_WORKERS=8 OOM风险 (可用RAM仅2.5GB) → 改4路并行

## 优化后的时间线

```
14:45  资金流预采集  (stock_fund_flow.fetch_and_cache_today)
15:30  writing 数据采集 (collect_data)
16:00  K线更新 (daily_kline_update, 脚本模式)
16:00  writing 文章生成+草稿箱→QQ通知你
17:00  策略信号扫描→QQ推送 (b60f3c86dd1b)
```

## 删除的cron

| cron | 原因 |
|:-----|:-----|
| 18619f5cdf16 雪球每日发布(16:30) | 用户要求不再使用 |
| 704e9bfe5896 18:00复盘提醒 | 合并入16:00文章推送步骤 |

## 注意事项

- 17:00的资金流数据来源于14:45预采集缓存, 若缓存缺失默认ff_score=50(中性)
- 17:00避开了晚间API黑窗(19:00-08:00), 北向资金走AKShare/stock-sdk均可
- spillover bug的根治方案不是加检查逻辑, 而是把cron移到足够早的时间

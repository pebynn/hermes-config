# A股收盘后数据管线 — 生产配置 (2026-05-13)

## 时序

```
15:30  afff56398abe  K线更新          LLM驱动  ~3-5min  daily_kline_update.py
15:40  81c6af2f5573  资金流预采集      no_agent  <1min    precache_fund_flow.sh
15:50  18edaa02cd7e  两融数据拉取      no_agent  <1min    precache_margin.sh
16:10  0637e225e375  三策略信号+QQ投递  no_agent  ~2min    run_daily_signals.sh → daily_signals.py
```

## 依赖关系

- K线数据 → 资金流(需收盘价) → 信号扫描(需全部数据)
- 10分钟间隔确保上游完成
- K线从no_agent切LLM驱动：no_agent有120s硬超时，脚本需3-5min

## 已删除

b60f3c86dd1b (信号引擎Pipeline调度) — 删除原因：该cron每天创建P2因子计算kanban任务给finance-domain，让其从零用LLM实现因子计算→必然卡死。因子计算已内置在daily_signals.py中(compute_factors_A等函数)，无需独立kanban pipeline。

# b60f3c86dd1b Cron 优化记录 — 2026-05-07

## 原始问题

cron `b60f3c86dd1b`（晚间合并：多因子回测+信号日报）调度为每日21:00，运行了两个全市场扫描脚本连续执行：

1. `mid_cap_strategy.py --signal --output /tmp/midcap_signal.json`
2. `daily_signal_report.py`（文本输出到 stdout）

2026-05-07 首次运行失败，session 持续37分钟后超时。根因分析：

- **模块名错误**：prompt 写 `from mid_cap_multi_factor import MidCapMultiFactor`，文件不存在。正确是 `mid_cap_strategy.py --signal --output`
- **方法不存在**：`strategy.run_daily()` 不存在
- **双重扫描**：两个脚本各自调用 `signal_engine.scan_signals()` 全市场扫描，做两遍相同工作
- **行业中性化 O(N²)**：`_neutralize_industry_zscores` 中每个因子循环用 `(df["_industry"] == x).sum()` 逐行全列比较，600只×12因子×100行业≈4.3M次操作。已修复为 `value_counts()` 预计算（O(N)）
- **policy_detect.py 13步网络瓶颈**：最严重的瓶颈。`policy_detect.py` 调用 akshare 拉取政策新闻数据，13步顺序HTTP下载，每步约400秒，总计约87分钟。两个脚本各调用一次 policy_detect = 双重浪费

## 修复内容

1. 模块名/方法名：使用正确的 CLI `mid_cap_strategy.py --signal --output /tmp/midcap_signal.json`
2. 消除冗余：只运行 `mid_cap_strategy.py --signal` 一次全市场扫描，agent 解析 JSON 生成文本日报
3. O(N²) → O(N)：`signal_engine.py` L414-421 行业中性化改为预计算 `value_counts()`
4. 对标 writing-domain：K线(16:00)+两融(16:15)前置采集 → 21:00 只扫描不拉数据

## 剩余瓶颈

**policy_detect.py** 的 13 步 akshare 网络下载（约87分钟）尚未解决。这将主导扫描耗时，即使其他瓶颈全部消除。

建议方案：
- 方案A：policy_detect 结果缓存到本地（24小时有效），避免每次扫描重新拉取
- 方案B：policy_detect 改为独立前置 cron（如16:30），写入缓存文件，主扫描 cron 读取

## 借鉴模式

writing-domain 的分阶段管线：数据采集(15:30) → 复盘生成(16:00)，计算任务不重复拉数据。

finance-domain 对应：K线(16:00) + 两融(16:15) + 政策(待加) → 信号扫描(21:00)

## 僵尸进程问题

旧运行失败后的 worker 进程（8个 daily_signal_report 子进程）持续占用CPU。重新运行前必须 `pkill -9` 清理。

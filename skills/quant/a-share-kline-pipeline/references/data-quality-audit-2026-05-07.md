# finance-domain 数据准确性审计 (2026-05-07)

对 ~/quant/ 下 25 个 Python 文件的数据验证机制和雪球数据源集成机会的全面审计。

## 一、审计结论

**数据源冗余设计良好，但数据准确性验证几乎为零。**
- ✅ 多层 fallback：Tushare→AKShare→(腾讯/东方财富)
- ❌ 无跨源交叉验证：两源都成功时从不对比
- ❌ 无写入前校验：涨跌幅/OHLC关系/成交额=0 等未检查
- ❌ 无端到端一致性：写入行数/日期/抽样抽查未做

## 二、关键发现

### 2.1 致命缺失：backfill_today_mysql.py NaN→0 静默转换

位置：`backfill_today_mysql.py` L49-57

```python
# 当前代码 — 有数据污染风险
for col in ["open","close","high","low","amount","amplitude","pct_chg","change","turnover"]:
    val = renamed.get(col, 0)
    if pd.isna(val) or val is None:
        renamed[col] = 0  # ← 静默将 NaN 转为 0，无任何告警
```

风险：parquet 缓存中若某只股票数据缺失（列全 NaN），会被静默写入 MySQL 为 0 值。之后策略脚本读取时无法区分"真实收盘 0 元"和"数据缺失"。0 元收盘价 A 股不可能出现，但 NaN 被转 0 后失去了这个信号。

修复：保留 NaN，仅 volume 特殊处理（真实成交量可能为 0），其他列保留 NaN 并记录告警日志。

### 2.2 pre-write validation 完全缺失

所有数据导入脚本（daily_kline_update / backfill_today_mysql / bulk_import_to_mysql / import_kline_to_mysql）均无以下检查：

| 检查项 | 规则 | 影响 |
|:--------|:-----|:-----|
| 涨跌幅范围 | 主板 ±10%, 创业/科创板 ±20% | 数据错误检测 |
| OHLC 关系 | open≤high, low≤close, low≤high | 数据完整性 |
| 成交额=0 | volume>0 但 amount=0 矛盾 | 数据一致性 |
| 收盘价跳变 | 与前日差异 >30% | 异常检测 |
| 停牌中误报 | volume=0 但 amount>0 矛盾 | 数据逻辑 |

建议：新建 `~/quant/validate_kline.py` 统一校验模块，供所有导入脚本调用。

### 2.3 Tushare/AKShare 交叉验证缺失

当前逻辑：Tushare成功→直接用，不再查AKShare。两个源都成功时从不对比。

风险：Tushare 返回错误数据（如某只股票价格错位、unit conversion 错误）会被静默吞入。2026-05-06 发现的振幅公式错误就是典型：Tushare路径用 pre_close，AKShare路径用 low 做分母，两个路径振幅值不一致但从未被对比发现。

修复：Tushare 成功拉取后，随机抽样 50-100 只用 AKShare 获取对比，差异 >0.5% 告警不阻断。

### 2.4 晚间不可用 (AKShare push2 黑窗 19:00-08:00)

| 脚本 | 失败点 | 影响 |
|:-----|:-------|:-----|
| daily_kline_update.py L362 | AKShare stock_zh_a_daily | Tushare失败后无夜间回退 |
| signal_engine.py L1100 | AKShare 北向资金 | 北向乘数缺失（有保护） |
| data_common.py L167 | AKShare stock_info_a_code_name | 缓存过期后清单为空 |
| precache_financial.py | AKShare stock_financial_abstract_ths | 财务数据拉取失败 |

Xueqiu（雪球）作为 24/7 可用数据源，是解决夜间不可用的最佳补充。

### 2.5 已知 Bug（代码中未发现引用）

- **prefetch_capflow look-ahead**：代码全量搜索 0 结果。可能存在于独立脚本或已删除的遗留代码。
- **calc_capital_resonance 全返25分**：怀疑指向 signal_engine.py 的 `_compute_layer4()` L612-832，融资余额 trend 分数线上溢。

## 三、雪球数据源集成最佳插入点

现有基础设施：`xueqiu_kline.py` (XueqiuSource 类) + `kline_fallback.py` (晚间降级 wrapper)

### ★★★ 最高价值

| 插入点 | 位置 | 价值 | 状态 |
|:-------|:-----|:-----|:-----|
| daily_kline_update.py 雪球第三级回退 | L498-500 (Tushare失败→直接AKShare) | 夜间可用，批量接口速度快 | ✅ v2.1已完成 |
| daily_kline_update.py 雪球交叉验证 | L475-485 (写入缓存循环之前) | 首次引入真正的 cross-source validation | 待实现 |
| signal_engine.py 北向资金雪球 fallback | L1100-1108 | 消除晚间北向数据缺失 | 待实现 |

### ★★ 高价值

| 插入点 | 位置 | 价值 | 状态 |
|:-------|:-----|:-----|:-----|
| backfill_today_mysql.py 导入前雪球抽样 | L20 清空后 L29 导入前 | 防大范围数据错误污染 MySQL | 待实现 |
| daily_kline_update.py 雪球指数哨兵 | L471 (过滤后写入前) | 对比 4 大指数检测交易日异常 | 待实现 |

## 四、优先级修复清单

### P0 — 紧急（本周）

| ID | 问题 | 动作 |
|:---|:-----|:-----|
| P0-1 | NaN→0 静默转换 | 保留 NaN 并加告警日志 |
| P0-2 | 缺少 pre-write validation | 新建 validate_kline.py 模块 |
| P0-3 | 缺少雪球夜间回退 | ✅ **已完成 (2026-05-07)** daily_kline_update.py v2.1 插入雪球 fallback |

### P1 — 重要（本月）

| ID | 问题 | 动作 |
|:---|:-----|:-----|
| P1-1 | 无 Tushare/AKShare 交叉验证 | 抽样对比 close，差异>0.5%告警 |
| P1-2 | 北向资金晚间不可用 | 加雪球 fallback |
| P1-3 | 端到端一致性验证缺失 | 写入后验证行数/日期 | ✅ **已完成 (2026-05-07)** — verify_write() 已添加到 data_common.py，backfill_today_mysql.py 和 daily_kline_update.py 均已调用。详见 references/end-to-end-write-verification.md |
| P1-4 | calc_capital_resonance 全返25分 | 定位+修复 |

### P2 — 优化（下季度）

| ID | 问题 | 动作 |
|:---|:-----|:-----|
| P2-1 | 数据血统追踪缺失 | kline 表加 source 列 |
| P2-2 | bulk_import 无去重 | 加 upsert 逻辑 |
| P2-3 | 数据质量仪表板 | 新建 data_quality_report.py |

## 五、建议新增文件

1. `~/quant/validate_kline.py` — 统一数据校验模块
2. `~/quant/cross_check.py` — 多源交叉验证模块
3. `~/quant/data_quality_report.py` — 数据质量日报

## 六、审计覆盖率

- 审计文件：25 个 Python 文件
- 深度审查：daily_kline_update.py, backfill_today_mysql.py, signal_engine.py, data_common.py, xueqiu_kline.py, kline_fallback.py
- 结构审查：bulk_import_to_mysql.py, import_kline_to_mysql.py, precache_kline.py, precache_financial.py, margin_data.py, volume_indicators.py, chan_buy_signal.py, tushare_data_pipeline.py
- 扫描但未深读：download_kline_2020.py, clean_parquet_today.py, convert_kline_to_csv.py, normalize_kline_cache.py, check_cache.py, check_cache_v2.py, debug_cache.py, mid_cap_strategy.py, policy_detect.py, db_web.py, daily_signal_report.py

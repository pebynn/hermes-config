# 数据采集陷阱（2026-05-05 实战验证）

## ❌ 致命bug: `iloc[-1]` 总是返回最新日数据

`collect_data.py` 旧代码：
```python
df = ak.stock_zh_index_daily_em(symbol=symbol)
latest = df.iloc[-1]  # BUG: 始终取最后一行，忽略 date_str
```

`stock_zh_index_daily_em` 返回完整历史数据（1990年至今），但 `iloc[-1]` 始终取最新交易日。用户传入 `--date 2026-04-28`，拿到的仍是 2026-04-30 的数据。

**修复**：
```python
df["date"] = df["date"].astype(str)
target_rows = df[df["date"] == date_str]
if target_rows.empty:
    print(f"⚠️ {date_str} 无数据")
    return {}
idx = target_rows.index[0]
latest = df.loc[idx]
prev = df.loc[idx - 1] if idx > 0 else None
```

## ❌ 非交易日无校验，采集到假数据

2026-05-01（劳动节假期）没有交易数据，但采集脚本未检查日期有效性，将实时端点返回的最新数据误存为假期日数据。这导致周总结聚合时所有字段被污染。

**修复**：采集前用上证指数校验日期：
```python
check_df = ak.stock_zh_index_daily_em(symbol="sh000001")
check_df["date"] = check_df["date"].astype(str)
if check_df[check_df["date"] == date_str].empty:
    print(f"❌ {date_str} 非交易日，停止采集")
    return None
```

## ❌ 实时端点不支持历史日期 → 部分已有替代方案

以下 AKShare 端点**不支持 date 参数**，始终返回最新数据：

| 端点 | 影响字段 | 是否有替代？ |
|------|---------|-------------|
| `stock_market_fund_flow()` | 主力资金流向 | ❌ 无免费替代，需 Tushare Pro `moneyflow_mkt_dc` (6000积分≈600元) |
| `stock_board_industry_name_em()` | 行业板块 | ⚠️ 当日实时采集OK，不可回填历史 — 见下方 |
| `stock_board_concept_name_em()` | 概念板块 | ⚠️ 当日实时采集OK，不可回填历史 |
| `stock_sector_fund_flow_rank(indicator="今日")` | 行业资金流向 | ❌ 无免费替代，需 Tushare Pro `moneyflow_dc` (2000积分) |

### ❌ stock_board_industry_hist_em() 实测仅至2022年，不可用于当前回填

### ❌ stock_board_industry_hist_em() 实测仅至2022年，不可用于当前回填

**发现日期**: 2026-05-05 本轮改造

之前以为 `stock_board_industry_hist_em(symbol="板块名")` 返回全量历史数据，可用于按日期过滤得到当日板块涨跌幅。**实测发现**该端点数据仅截至2022年左右，当前日期的查询返回空。不可用于历史回填或周累计计算。

**正确方案（已在当前管线中实现）**：

板块涨跌幅使用 `stock_board_industry_name_em()` 当日实时采集，存入每日 `all_data.json` 的 `sectors.industry` 字段，各日数据独立保存。周总结时扫描各日 JSON：
- 统计板块出现频率（频率 × 3 加权评分）
- 使用末日涨跌幅作为参考（非累计值，命名已改为 `daily_change`）
- 不累加多日涨跌幅（避免假数据）

**如需历史回填（2022年前板块数据）**：
- 方案A：Tushare Pro `dc_index_daily`（2000积分）
- 方案B：东方财富API直连
- 方案C：Tushare Pro `moneyflow_dc`（含板块涨跌数据）

## ✅ 板块涨跌幅累加 = 假信号（当前管线已正确规避）

因为 `stock_board_industry_name_em()` 始终返回最新板块数据，在周总结中按天累加（`+=`）会导致假数据：某板块在4个交易日各出现一次且涨跌幅均为 +9.46% → 累计 +37.84%，但这是同一个数字乘了4。**当前管线已正确规避**：`weekly_summary.py` 不累加，每次用最后一次出现的涨跌幅覆盖赋值（`=` 而非 `+=`），字段名 `daily_change`，prompt 中标注"最新"而非"累计"。

**验证信号**：如果周总结中出现板块"累计涨幅 +37.84%"（4天 × 9.46%），说明代码回退到了旧逻辑。

## ❌ 主力资金逐日全相同 → 跳过

`stock_market_fund_flow()` 无 date 参数，历史采集的每日主力资金均相同。周总结会算出 `-520亿 × 4 = -2081亿` 的假周合计。

**修复**：在 `build_weekly_prompt()` 中检测逐日资金流是否全相同：
```python
has_reliable_mf = len(set(d["flow"] for d in weekly["daily_main_force_flow"])) > 1
```
若全相同则在 prompt 中跳过主力资金段，标注"历史数据不可用"。

## ❌ `data_completeness` 标记无条件 True — 元数据谎报（2026-05-06 发现）

**根因**：`collect_data.py` 中5处 `data_completeness` 标记都在 try/except **外部**无条件设为 `True`。即使 API 全部失败、数据为空字典，元数据仍然声称"完整"。下游代码信任 `data_completeness` 后发现数据缺失，导致图表跳过或文章段落为空。

**修复**：5处改为条件判断：
```python
# ❌ 旧
data["data_completeness"]["sectors"] = True

# ✅ 新 — 仅当实际采集到数据
data["data_completeness"]["sectors"] = len(data["sectors"].get("industry", [])) > 0
data["data_completeness"]["main_force_flow"] = bool(data["capital_flow"].get("main_force", {}).get("net_inflow") is not None)
data["data_completeness"]["sector_flow"] = bool(data["capital_flow"].get("sector_flow", {}).get("inflow_top5"))
data["data_completeness"]["indices"] = any(v and v.get("index") for v in data["market"].values() if isinstance(v, dict))
# limit_up_down: 检查 total > 0
```

**受影响脚本**：`skills/a-share-data-collector/scripts/collect_data.py`

## ⚠️ 涨跌停数据结构：两种格式

`limit_up`/`limit_down` 字段实际有两种格式：
```json
// 格式1（旧）
["股票1", "股票2", ...]

// 格式2（新，当前使用）
{"total": 58, "samples": [{"name": "...", "code": "...", ...}, ...]}
```

`weekly_summary.py` 已适配两种格式，但其他消费方需注意。

## ❌ `generate_charts.py --weekly` 参数不存在 → 周总结静默无图

`weekly_summary.py` 的 `generate_weekly_charts()` 旧代码调用：
```python
subprocess.run([sys.executable, str(CHARTS_SCRIPT), "--date", date_str, "--weekly"], ...)
```
但 `generate_charts.py` 不支持 `--weekly` 参数，导致图表生成静默失败，周总结文章无配图。

**修复**：移除 `--weekly` 参数，`generate_charts.py` 不需要区分 daily/weekly，同一套图表即可。

**额外修复**：`weekly_summary.py` 新增 Step 2b（自动采集兜底）——若当日 RAW_DIR 数据缺失，自动调用 `collect_data.py` 补采。

---

## 验证规则

每次修改采集脚本后必须验证：
1. 连续3个不同交易日的数据是否真的不同（指数值、涨跌幅、成交额、涨停数）
2. 非交易日是否被正确拒绝
3. 涨停/跌停数据格式是否正确

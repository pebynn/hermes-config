# Sina 财经 API 字段映射

## ⚠️ 致命陷阱

Sina `hq.sinajs.cn` 返回格式：`名称,今开,昨收,收盘,最高,最低,成交量,成交额,...`

**极易搞错：`parts[1]` 是今开，不是收盘！**

2026-05-06 之前的代码将 `parts[1]` 当作收盘、`parts[3]` 当作今开，导致所有涨跌幅全部算错。

## 正确映射 (A股指数 sh/sz)

| fields index | 含义 | 上证示例 | 备注 |
|:--|:--|:--|:--|
| parts[1] | **今开** (open) | 4135.45 | ⚠️ 易错点！ |
| parts[2] | **昨收** (prev_close) | 4112.16 | |
| parts[3] | **收盘** (close) | 4160.17 | |
| parts[4] | **最高** (high) | 4166.15 | |
| parts[5] | **最低** (low) | 4129.91 | |
| parts[8] | 成交量 (手) | 701177480 | |
| parts[9] | **成交额 (元)** | 1465903193400 | ⚠️ 单位是元！/1e8 = 亿 |

### 成交额换算铁律

**parts[9] 单位是元，不是万元！**

```python
# ✅ 正确：元 → 亿元
turnover = safe_float(parts[9]) / 1e8    # 1465903193400 / 1e8 = 14659.03 亿

# ❌ 错误：假设单位是万元
turnover = safe_float(parts[9]) / 10000  # 1465903193400 / 10000 = 146590319.34 (万元，不是亿！)
```

**已知错误**: `data_collector_seo.py` L193 误用 `/10000` 并注释 `parts[9]=成交额(万)`，实际得到万元而非亿元。字段名 `turnover` 全管线统一为亿元。

## 东方财富 push2 对照验证

| 字段 | 含义 | 上证示例 |
|:--|:--|:--|
| f43 | 最新价/收盘 | 416017 (=4160.17) |
| f60 | 昨收 | 411216 (=4112.16) |
| f170 | 涨跌幅 | 117 (=1.17%) |

用东方财富 f43/f170 交叉验证 Sina 的 parts[3]/涨跌幅。

## 涨跌幅计算

```python
close = float(parts[3])      # 收盘 ← 正确
prev_close = float(parts[2]) # 昨收
pct = (close - prev_close) / prev_close * 100
```

## 修复记录

- **2026-05-09 审计**: 发现 data_collector_seo.py 成交额 `/10000` 错误，应 `/1e8`。发现 fallback_pipeline.py fields[1]标为"当前价"实为今开、fields[3]标为"今开"实为收盘。
- **2026-05-06**：`collect_data.py` 的 `validate_indices_with_sina()` 中字段映射修正。`parts[1]` → `sina_open`，`parts[3]` → `sina_close`。
- **影响范围**：早前所有使用 Sina 数据的涨跌幅（上证+0.57% 实为 +1.17%，偏差 0.60%）。

---

# 美股指数 (gb_dji / gb_ixic / gb_inx)

端点: `https://hq.sinajs.cn/list=gb_dji,gb_ixic,gb_inx`

## ⚠️ 致命陷阱：parts[2] 不是涨跌幅！

2026-05-09 实测验证：Sina 美股全球指数 gb_xxx 格式与 A 股完全不同，且官方无可靠文档。
**parts[2] 的值不等于真实涨跌幅**（DJI: parts[2]=0.02 但真实涨跌幅=-1.79%）。

**安全做法：只用 parts[1](当前价) 和 parts[8](昨收) 计算 change_pct，不用 parts[2]。**

## 实测验证数据 (2026-05-09 19:00 CST)

gb_dji 完整输出：
```
道琼斯,49609.1602,0.02,2026-05-09 04:47:04,12.1900,49581.0898,49830.6992,49486.9609,50512.7891,41354.0898,456512707,500537135,0,0.00,--,0.00,...,May 8 04:46PM EDT,49596.9688,0,1,2026
```

| fields index | 含义 | DJI示例 | 验证 |
|:--|:--|:--|:--|
| parts[0] | 名称 | 道琼斯 | ✅ |
| parts[1] | **当前价(盘后最新)** | 49609.16 | ✅ |
| parts[2] | 盘后涨跌幅(近似,勿用!) | 0.02 | ❌ 真实涨跌幅=-1.79% |
| parts[3] | 时间戳 | 2026-05-09 04:47:04 | ✅ |
| parts[4] | 盘后变动额(当前价-收盘价) | 12.19 | ✅ 49609.16-49596.97≈12.19 |
| parts[5] | **今开** | 49581.09 | ✅ |
| parts[6] | **最高** | 49830.70 | ✅ |
| parts[7] | **最低** | 49486.96 | ✅ |
| parts[8] | **昨收** | 50512.79 | ✅ 非之前误标的"52周最高" |
| parts[9] | 52周最低/其他 | 41354.09 | ⚠️ 含义待确认 |
| parts[26] | **正式收盘价(当日)** | 49596.97 | ✅ 与parts[4]交叉验证 |

## 涨跌幅计算铁律

```python
# ✅ 正确：从当前价和昨收计算
close = safe_float(parts[1])
prev_close = safe_float(parts[8])
change_pct = round(calc_change_pct(close, prev_close), 2)
# DJI: (49609.16 - 50512.79) / 50512.79 * 100 = -1.79%

# ❌ 错误：直接取 parts[2]
change_pct = safe_float(parts[2])  # 0.02, 完全错误!
```

⚠️ 与 A 股指数格式**完全不同**：
- A股 parts[1]=今开, parts[2]=昨收, parts[3]=收盘
- 美股 parts[1]=当前价, parts[2]=近似涨跌幅(勿用!), parts[3]=时间戳, parts[8]=昨收
- 美股**没有直接的涨跌幅字段**，必须从 close/prev_close 计算

---

# A50 期货 (hf_CHA50CFD)

端点: `https://hq.sinajs.cn/list=hf_CHA50CFD`

⚠️ 符号是 `hf_CHA50CFD`，**不是** `hf_XIN`（后者为空）。

响应格式: `var hq_str_hf_CHA50CFD="最新价,涨跌额,买入,卖出,最高,最低,时间,今开,昨收,成交量,..."`

| fields index | 含义 | 示例 |
|:--|:--|:--|
| parts[0] | **最新价 (close)** | 15783.80 |
| parts[1] | 涨跌额 | (可能为空) |
| parts[2] | 买入价 | 15790.00 |
| parts[3] | 卖出价 | 15791.00 |
| parts[4] | **最高** | 15909.00 |
| parts[5] | **最低** | 15701.00 |
| parts[6] | 时间 | 14:51:57 |
| parts[7] | **今开** | 15816.00 |
| parts[8] | **昨收** | 15812.00 |
| parts[9] | 成交量 | 929902 |

涨跌幅需手动计算: `(parts[0] - parts[8]) / parts[8] * 100`

---

# 恒生指数 (int_hangseng)

端点: `https://hq.sinajs.cn/list=int_hangseng`

⚠️ 此端点**仅返回 4 个字段**，不含开盘/最高/最低。

响应格式: `var hq_str_int_hangseng="恒生指数,最新价,涨跌额,涨跌幅"`

| fields index | 含义 | 示例 |
|:--|:--|:--|
| parts[0] | 名称 | 恒生指数 |
| parts[1] | **最新价 (close)** | 26626.65 |
| parts[2] | 涨跌额 | 412.87 |
| parts[3] | **涨跌幅(%)** | 1.58 |

OHLC 补全：当 Sina HSI 降级时，open/high/low 填充为 0.0。下游消费者（如 build_brief 的 format_change）应仅依赖 close/change_pct。

---

# 格式差异速查表

| 数据源 | parts[1] | parts[2] | parts[3] | parts[8] | 涨跌幅获取方式 |
|:--|:--|:--|:--|:--|:--|
| **A股指数** | 今开 | 昨收 | **收盘** | — | `calc_change_pct(parts[3], parts[2])` |
| **美股指数** | **当前价** | ⚠️勿用 | 时间戳 | **昨收** | `calc_change_pct(parts[1], parts[8])` |
| **A50期货** | 涨跌额 | 买入价 | 卖出价 | **昨收** | `calc_change_pct(parts[0], parts[8])` |
| **恒生指数** | **收盘** | 涨跌额 | **涨跌幅%** | — | `parts[3]` 直接取 |

**核心规律**: A股和全球指数格式完全不同，绝不能混用！涨跌幅统一用 `calc_change_pct()` 计算。

---

## 修复记录

- **2026-05-09 审计(重大修正)**: 美股指数映射全面修正！parts[8]实为昨收(非"52周最高")，parts[2]为盘后近似涨跌幅(非可靠涨跌幅)。DJI实测: parts[2]=0.02 但真实涨跌幅=-1.79%。新增 calc_change_pct() 统一函数到 shared_utils.py，全管线16处自行计算涨跌幅替换为统一函数。修复 generate_charts.py 缩进断裂、data_collector_seo.py 成交额/1e8、fallback_pipeline.py 映射修正、morning_brief.py 美股涨跌幅修正、safe_float漂移清理。
- **2026-05-09 审计(初始)**: 发现 data_collector_seo.py 成交额 `/10000` 错误应 `/1e8`；发现 fallback_pipeline.py fields[1]标为"当前价"实为今开、fields[3]标为"今开"实为收盘；新增格式差异速查表和成交额换算铁律
- **2026-05-07**：新增美股/A50/恒生指数字段映射。修正 A50 符号 `hf_XIN` → `hf_CHA50CFD`。发现 HSI 端点仅4字段。
- **2026-05-06**：`collect_data.py` 的 `validate_indices_with_sina()` 中字段映射修正。`parts[1]` → `sina_open`，`parts[3]` → `sina_close`。

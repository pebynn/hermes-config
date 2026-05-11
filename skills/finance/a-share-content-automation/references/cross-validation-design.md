# 多平台交叉验证设计

collect_data.py 集成的自动数据验证系统。
# 多平台交叉验证设计 (v2 — 2026-05-07 升级为3-way)

collect_data.py 集成的自动数据验证系统。现已从 AKShare↔Sina 2-way 升级为 AKShare↔Sina↔雪球 3-way。

## 架构

```
collect_data.py
  ├─ AKShare 主采集（可能超时/断连）
  ├─ validate_indices_with_sina()      → Sina hq.sinajs.cn 指数对比
  ├─ validate_sectors_with_sina()      → Sina 行业板块对比
  ├─ validate_indices_with_xueqiu()    → 🆕 雪球 batch/quote.json 指数对比 (L265)
  ├─ fill_indices_from_xueqiu()        → 🆕 反向自动填充：AKShare缺失时雪球回填 (L349)
  ├─ validate_xueqiu_vs_sina()         → 🆕 雪球 vs 新浪直接对比 (L405)
  └─ 写入 _cross_validation 到 all_data.json
```

## 三级降级链（晚间黑窗19:00-08:00）

```
AKShare (push2) → 超时30s → Sina (仅指数) → 缺失 → 🆕 雪球 (全维度) → 反向回填
```

## 验证规则

### 指数数据

| 条件 | 状态 | 行为 |
|:--|:--|:--|
| 涨跌幅差 ≤ 0.05% | ok | 通过 |
| 涨跌幅差 0.05%~0.5% | minor | 记录但不警告 |
| 涨跌幅差 > 0.5% | mismatch | ⚠️ 标记偏差，自动用 Sina 修复 |
| 任一源不可用 | failed | 保留可用源数据 |

### 雪球 vs 新浪直接对比（新增）

| 条件 | 状态 |
|:--|:--|
| 四个指数涨跌幅差均 ≤ 0.05% | ok |
| 任一指数涨跌幅差 > 0.5% | mismatch（标记 discrepancy） |
| 任一源不可用 | failed |

## 自动修复逻辑

### AKShare → Sina（已有）
```python
if result["status"] == "mismatch" and our_data.get("index", 0) == 0:
    data["market"][key] = {sina数据, "_source": "Sina (corrected from AKShare failure)"}
```

### 🆕 雪球 → AKShare 反向填充 (fill_indices_from_xueqiu)
```python
# 当 AKShare 指数数据缺失（index=0 或 change_pct=0）时
# 从雪球 batch/quote.json 快照数据回填
# amount 自动 /1e8 转亿，附加 _source 标注
data["market"][key] = {
    "index": xq_data["current"],
    "change_pct": xq_data["percent"],
    "open": xq_data["open"], "high": xq_data["high"], "low": xq_data["low"],
    "turnover": xq_data["amount"] / 1e8,
    "_source": "Xueqiu (corrected from AKShare failure)"
}
```

## 输出格式 (v2)

```json
{
  "_cross_validation": {
    "indices": {
      "source": "Sina Finance (hq.sinajs.cn)",
      "status": "critical",
      "discrepancy_count": 4,
      "discrepancies": ["shanghai: our=+0.00% vs sina=+0.57%"],
      "results": { ... }
    },
    "sectors": {
      "source": "Sina Finance (vip.stock.finance.sina.com.cn)",
      "status": "ok",
      "results": {"sina_count": 20, "our_count": 34, "matched": 17, "big_diffs": 0}
    },
    "xueqiu": {
      "source": "Xueqiu (stock.xueqiu.com)",
      "status": "ok",
      "results": {
        "shanghai": {
          "our": {"close": 4160.17, "change_pct": 1.17},
          "xueqiu": {"close": 4160.17, "change_pct": 1.17},
          "diff": {"close": 0.0, "change_pct": 0.0},
          "status": "ok"
        }
      }
    },
    "xueqiu_vs_sina": {
      "source": "Xueqiu vs Sina cross-check",
      "status": "ok",
      "results": {
        "shanghai": {
          "sina": {"close": 4160.17, "change_pct": 1.17},
          "xueqiu": {"close": 4160.17, "change_pct": 1.17},
          "diff": {"close": 0.0, "change_pct": 0.0},
          "status": "ok"
        }
      }
    }
  }
}
```

## 雪球集成关键细节

### 字段映射

雪球 `batch/quote.json` 返回字段名不同于 AKShare/Sina：
- `current` = 收盘价（对应 AKShare 的 `index`）
- `percent` = 涨跌幅%
- `amount` = 成交额（元，需 /1e8 转亿）
- `volume` = 成交量（股）

`validate_indices_with_xueqiu()` 内部归一化为 `close`/`change_pct`，下游函数无需关心原始字段名。

### 模块位置

双域共享基础设施：`~/quant/xueqiu_kline.py`
- writing-domain：`collect_data.py` 从 `~/quant/` import
- finance-domain：`daily_kline_update.py` 降级用（未来）

### Cookie 过期优雅降级

`XueqiuSource.is_available()` 返回 False 时，`validate_indices_with_xueqiu()` 返回 `status: "failed"` 不阻塞采集管线。
      "discrepancy_count": 0,
      "results": {
        "shanghai": {
          "our": {"close": 4135.45, "change_pct": 0.57},
          "xueqiu": {"close": 4135.50, "change_pct": 0.58, "open": ..., "high": ...},
          "diff": {"close": 0.05, "change_pct": 0.01},
          "status": "ok"
        }
      }
    },
    "xueqiu_vs_sina": {
      "source": "Xueqiu vs Sina cross-check",
      "status": "ok",
      "discrepancy_count": 0,
      "results": {
        "shanghai": {
          "sina": {"close": 4135.45, "change_pct": 0.57},
          "xueqiu": {"close": 4135.50, "change_pct": 0.58},
          "diff": {"close": 0.05, "change_pct": 0.01},
          "status": "ok"
        }
      }
    }
  }
}
```

## 🆕 fill_indices_from_xueqiu() — 雪球反向自动填充

当 AKShare 指数数据缺失（`index==0` 或 `change_pct==0`）时，从雪球验证结果回填数据到 `data["market"][key]`。

**填充字段**：index/open/high/low/turnover(volume/1e8转亿)/_source

**触发条件**：
```python
if our_index == 0 or our_pct == 0:
    if xq_close is not None and xq_close != 0:
        # 回填
```

**Returns**：`{"filled": [{"key", "original_index", "backfilled_index", ...}], "total_filled": N}`

**关键**：雪球 volume 单位是元（成交额），除以 1e8 转为亿后存入 turnover。

## 🆕 validate_xueqiu_vs_sina() — 雪球 vs 新浪直接对比

逐项对比四大指数（shanghai/shenzhen/cyb/kc50）的雪球和新浪数据。

**对比字段**：close, change_pct

**阈值**：pct_diff > 0.5% → mismatch；> 0.05% → minor

**Returns 格式**：与 `validate_indices_with_sina()` 一致，`results[key]` 含 `sina`/`xueqiu`/`diff`/`status`。

**调用时机**：在 `fill_indices_from_xueqiu()` 之后执行，确保填充后的数据参与对比。

## 关键陷阱

### Sina 字段映射（致命）

Sina quote API 返回格式：`名称,今开,昨收,收盘,最高,最低,...`

```python
# ✅ 正确
sina_open = float(parts[1])       # 今开
sina_prev_close = float(parts[2]) # 昨收  
sina_close = float(parts[3])      # 收盘 ← 不是 parts[1]!

# ❌ 错误（2026-05-06 之前所有数据都错了）
sina_close = float(parts[1])      # 实际是今开
sina_open = float(parts[3])       # 实际是收盘
```

验证方法：用东方财富 push2 API 的 `f170`(涨跌幅×100) 交叉比对。

### 东方财富晚间不可用

push2/push2his API 北京时间 19:00-08:00 全部 RemoteDisconnected/Empty reply。
交叉验证在此期间自动降级为"failed"，不阻塞采集。

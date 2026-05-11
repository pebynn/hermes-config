# 数据格式陷阱

本会话发现的数据结构不一致问题。

## 涨停/跌停字段：list vs dict

`collect_data.py` 输出的 `limit_up`/`limit_down` 字段格式不稳定：

### 格式A：直接列表（旧版）
```json
{
  "limit_up_down": {
    "limit_up": [
      {"name": "宏英智能", "code": "001266", "change_pct": 10.01, ...},
      ...
    ],
    "limit_down": [
      {"name": "某股", "code": "000001", "change_pct": -9.98, ...},
      ...
    ]
  }
}
```

### 格式B：含总数的字典（新版）
```json
{
  "limit_up_down": {
    "limit_up": {
      "total": 58,
      "samples": [
        {"name": "宏英智能", "code": "001266", "change_pct": 10.01, ...},
        ...
      ]
    },
    "limit_down": {
      "total": 9,
      "samples": [
        {"name": "某股", "code": "000001", "change_pct": -9.98, ...},
        ...
      ]
    }
  }
}
```

### 影响脚本
- `weekly_summary.py` → `aggregate_weekly_data()` — 遍历 limit_up 时若按列表处理会遍历到字符串 key
- 错误表现：`AttributeError: 'str' object has no attribute 'get'`

### 适配代码（已应用）
```python
limit_up_raw = data.get("limit_up_down", {}).get("limit_up", {})
limit_up = limit_up_raw.get("samples", []) if isinstance(limit_up_raw, dict) else limit_up_raw
for s in limit_up:
    name = s.get("name", "") if isinstance(s, dict) else str(s)
    if name:
        weekly["limit_up_frequency"][name] += 1
```

## 行业数据重复

2026-05-01（劳动节）的 AKShare 数据显示与前一天完全相同（燃料电池 9.46%，亿华通-U）。非交易日采集到的数据是前一日缓存的副本。`weekly_summary.py` 的评分机制会将重复数据计入频率，人为抬高该板块的评分。

**建议**：采集前检查交易日历，非交易日跳过采集以获取真实周数据。

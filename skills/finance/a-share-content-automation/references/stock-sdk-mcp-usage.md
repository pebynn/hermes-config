# stock-sdk-mcp 数据源使用指南

stock-sdk-mcp 是基于腾讯数据源的 MCP Server，已全局安装在 `/home/pebynn/.hermes/node/bin/stock-mcp`。AKShare/东方财富 API 不可用时（晚间 19:00-08:00、反爬封锁等）的首选替代源。

## 数据源架构地位

```
AKShare (东方财富 push2) → 超时/封锁
  └─ Sina (hq.sinajs.cn, 仅指数)
       └─ 雪球 (xueqiu_kline.py, 24h可用)
            └─ stock-sdk-mcp (腾讯, 24h可用, 覆盖面最广) ✓ 首选
```

**原则**: 任何时候优先使用 stock-sdk-mcp。AKShare 仅在 stock-sdk-mcp 不可用且需要回填历史数据时使用。

## 可用端点速查

| 端点 | 用法 | 状态 (19:00-08:00) | 备注 |
|------|------|-------------------|------|
| `get_a_share_quotes(codes)` | 指数实时行情 | ✅ | 返回最新价/昨收/涨跌/成交额 |
| `get_market_overview(includeHK)` | 市场总览 | ✅ | 指数+北向+涨停跌停统计 |
| `get_zt_pool(date, type)` | 涨停/跌停股池 | ✅ | type="zt"或"dt"，含行业/连板数 |
| `get_northbound_realtime(direction)` | 北向资金 | ✅ | direction="north"或"south" |
| `get_fund_flow_rank(indicator, scope)` | 资金流排名 | ❌ fetch failed | 个股/行业资金流 |
| `get_industry_list()` | 行业板块列表 | ❌ fetch failed | 所有行业板块 |
| `get_history_kline(symbol, period, startDate, endDate)` | K线历史 | ❌ fetch failed | 日K线数据 |
| `get_kline_with_indicators(...)` | K线+技术指标 | ❌ fetch failed | 含均线 |

## 关键字段映射

### 指数行情 (get_a_share_quotes)
```
code: "000001"  # 注意不带 sh/sz 前缀
price: 4179.95  # 最新收盘价
prevClose: 4180.09  # 昨收
open/high/low: 今开/最高/最低
change: -0.14   # 涨跌点数
changePercent: 0  # 涨跌幅% (注意: 上证今日为0.00%)
amount: 133167307  # 成交额 (单位: 万元?)
volume: 697019094  # 成交量 (单位: 手?)
turnoverRate: 1.45  # 换手率%
```

### 市场总览 (get_market_overview)
```
indices: [array of index quotes]
northbound: [北向资金汇总]
ztCount: 98  # 涨停家数
dtCount: 2   # 跌停家数
boardChanges: [龙虎榜/异动]
```

### 涨停股池 (get_zt_pool) — 关键字段
```
total: 98  # 涨停总数
data[].name: "国安股份"
data[].code: "000839"
data[].continuousBoardCount: 1  # 连板数
data[].industry: "通信服务"     # 所属行业
data[].amount: 171910711        # 成交额
data[].firstBoardTime: "09:25:00"  # 首次封板时间
data[].sealAmount: 160388585    # 封单金额
data[].ztStatistics: "1/1"      # "累计涨停数/连板数"
```

## 涨跌家数获取方法

stock-sdk-mcp 不直接提供全A涨跌家数统计。可通过以下方式获取：

1. **北向成分股统计**: `get_market_overview().northbound[0].upCount/downCount/flatCount` — 仅覆盖沪/深股通标的
2. **逐只扫描**: 不推荐，数据量大

## 写入 all_data.json 的字段规范

```json
{
  "market": {
    "上证指数": {
      "index": 4179.95,
      "prev_close": 4180.09,
      "open": 4163.85,
      "change": -0.14,
      "change_pct": 0.0,
      "amount": 133167307,
      "volume": 697019094,
      "source": "stock-sdk-mcp (腾讯数据源)"
    }
  },
  "up_down_stats": {
    "up": 1905, "down": 1247, "flat": 83,
    "limit_up": 98, "limit_down": 2,
    "source": "stock-sdk-mcp (腾讯)"
  },
  "limit_up_down": {
    "limit_up": {"total": 98, "source": "stock-sdk-mcp zt_pool"},
    "limit_down": {"total": 2, "samples": ["深华发A", "振宏股份"], "source": "stock-sdk-mcp dt_pool"}
  },
  "_meta": {
    "accuracy": {
      "indices": {"level": "A", "source": "stock-sdk-mcp (腾讯数据源)"},
      "limit_up_down": {"level": "A", "source": "stock-sdk-mcp zt_pool/dt_pool"}
    },
    "collected_at": "2026-05-08 19:50:00"
  }
}
```

## 已知问题

1. **基金流接口晚间不可用**: `get_fund_flow_rank` 和 `get_industry_list` 晚间返回 fetch failed。此时应将 `data_completeness.sectors` 和 `data_completeness.main_force_flow` 设为 False。
2. **K线接口问题**: `get_history_kline` 和 `get_kline_with_indicators` 晚间均不可用。用之前缓存的 `kline_cache.json` 替代。
3. **北向资金可能为0**: 非交易时段北向数据可能显示为0，属正常现象，需在文章中标注。

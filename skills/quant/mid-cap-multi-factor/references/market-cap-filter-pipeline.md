# 市值过滤管道: stock-sdk MCP → JSON → 回测

## 数据获取

stock-sdk MCP 的 `get_all_a_share_quotes` 返回全市场5514只股票的实时行情，包含 `totalMarketCap`(亿元) 和 `circulatingMarketCap`(亿元) 字段。

```python
# MCP调用 (一次性):
mcp_stock_sdk_get_all_a_share_quotes(batchSize=500, concurrency=5, market="all")
# 返回 ~18MB JSON，包含全部5514只股票
```

## 解析脚本

```python
import json

# 读取MCP返回
with open('/tmp/hermes-results/call_XX_....txt') as f:
    raw = f.read()
outer = json.loads(raw)
inner = json.loads(outer['result'])

items = inner['data']  # list of dict with 'code', 'totalMarketCap', etc.

codes = []
for item in items:
    mv = item.get('totalMarketCap')
    code = item.get('code', '')
    if mv is None or mv == '' or mv == '-' or mv <= 0:
        continue
    mv = float(mv)
    # totalMarketCap 单位是亿元 (茅台 ~16831.64)
    if 50 <= mv <= 500:  # 50亿-500亿
        codes.append(code)

# 保存
with open('midcap_codes.json', 'w') as f:
    json.dump(codes, f)
```

## 回测集成

在 `strategy_v2.py` 的筛选阶段加载：

```python
# Market cap filter (50-500亿)
_midcap_codes = None
_midcap_path = Path(__file__).parent / "midcap_codes.json"
if _midcap_path.exists():
    with open(_midcap_path) as f:
        _midcap_codes = set(json.load(f))

universe = {c: g ... for c, g in ak.groupby("code")
            if ...
            and (_midcap_codes is None or c in _midcap_codes)}
```

`_midcap_codes is None` 保证文件不存在时回退到所有股票（向后兼容）。

## 实测结果 (2026)

| 池子 | 股票数 | 年化 | 回撤 | 胜率 |
|:--|--:|--:|--:|--:|
| 全市场-688/92 | 4028 | 1378% | -6.8% | 52.3% |
| +市值50-500亿 | 2586 | **743%** | -8.6% | 43.0% |
| 仅主板+市值 | — | — | — | — |

## 关键发现

**市值过滤在动量策略中反效果**: 被踢掉的<50亿小票是2026年动量alpha的主要来源。市值过滤更适合基本面多因子策略（关注估值合理性），不适合纯动量策略（小票动量弹性大）。

## tushare备选方案

tushare `daily_basic` 接口也可获取总市值，但免费版无权限：
```
抱歉，您没有接口(daily_basic)访问权限
```

stock-sdk MCP 是当前唯一可靠的全市场市值数据源。

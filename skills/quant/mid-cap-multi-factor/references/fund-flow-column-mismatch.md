# 资金流缓存列名不匹配 (2026-05-10 发现)

## 问题

stock_fund_flow.py 的 COL_MAP 映射期望通过 stock-sdk Node.js 脚本返回的 JSON 
字段包含 `mainNet`, `mainNetRatio`, `retailNet` 等键，映射为 `main_net`, 
`main_net_ratio`。

但实际缓存的 parquet 文件列名与这些键不匹配。

## 缓存实际列名

### fund_flow_2026-05-08.parquet (800 行)

| 列名 | 说明 |
|------|------|
| code | 股票代码 |
| name | 股票名称 |
| net_inflow | 净流入 |
| net_pct | 净流入占比 |
| super_large_in | 超大单流入 |
| large_in | 大单流入 |
| mid_in | 中单流入 |
| small_in | 小单流入 |
| close | 收盘价 |
| date | 日期 |

### fund_flow_2026-05-09.parquet (1466 行)

| 列名 | 说明 |
|------|------|
| code | 股票代码 |
| main_flow | 主力流入 |
| retail_flow | 散户流入 |
| mid_flow | 中单流入 |
| large_flow | 大单流入 |
| date | 日期 |

### sector_flow_2026-05-08.parquet (100 行)

| 列名 | 说明 |
|------|------|
| code | 板块代码 |
| name | 板块名称 |
| net_inflow | 净流入 |
| ... | 行业流向数据 |

## `_compute_fund_flow` 期望的字段

```python
COL_MAP = {
    "mainNet": "main_net",          # 不存在
    "mainInflow": "main_inflow",    # 不存在
    "mainOutflow": "main_outflow",  # 不存在
    "mainNetRatio": "main_net_ratio", # 不存在
    "retailNet": "retail_net",      # 不存在? (retail_flow 存在但格式不同)
    "totalFlow": "total_flow",      # 不存在
}
```

## 影响

query_fund_flow(code) 从预加载的缓存中过滤 code 匹配的行，但返回的字典中
`main_net` = 0.0 (不存在的 key 时 dict.get 返回默认值), 
`main_net_ratio` = 0.0。

→ _compute_fund_flow 始终返回 ff_score=50.0(中性), ff_main_net=0.0
→ 资金流维度权重 0.20 全部报废，只贡献恒定的 10 分(50×0.20)到综合分

## 根因

缓存写入脚本 (`stock_sdk_fund_flow.js` 或 `fetch_rank_top`/`fetch_today_fund_flow`) 
返回的 JSON 字段名与 `stock_fund_flow.py` 的 `COL_MAP` 不一致。

- fetch_today_fund_flow 调用 `stock_sdk_fund_flow.js --codes ...`  
  → 该 JS 脚本输出的字段与 Python 端期望的不同
- fetch_rank_top 调用 `stock_sdk_fund_flow.js --top 100` 
  → 同样字段不匹配
- 两套写入格式 (May 8 vs May 9) 表明代码或 stock-sdk 版本后来变更过

## 修复方案

### 步骤 1：确认 stock_sdk_fund_flow.js 实际输出字段

```bash
~/tools/quant_env/bin/python3 -c "
import subprocess, json
HOME = '/home/pebynn'
proc = subprocess.run(
    [HOME + '/.hermes/node/bin/node', HOME + '/quant/stock_sdk_fund_flow.js', '--codes', '600519,000858'],
    capture_output=True, text=True, timeout=30,
    env={'NODE_PATH': HOME + '/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules'}
)
if proc.returncode == 0:
    data = json.loads(proc.stdout)
    print('Fields:', list(data.get('data', [{}])[0].keys()) if data.get('data') else 'NO DATA')
"
```

### 步骤 2：更新 COL_MAP 匹配实际字段

根据步骤 1 的结果，修改 `stock_fund_flow.py` 中的 `COL_MAP` 映射关系。

### 步骤 3：更新 score 函数参数名

需要同步更新 `score_main_net`, `score_main_net_ratio`, `score_retail_net` 及
`compute_fund_flow_score` 中的字段引用，以匹配实际列名。

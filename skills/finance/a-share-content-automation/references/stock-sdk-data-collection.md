# stock-sdk 数据采集接入指南

## 背景

EastMoney IP 被封禁后，AKShare 全线不可用。stock-sdk（腾讯 qt.gtimg.cn 数据源）是从 Node.js 调用的可行替代方案。

## 安装状态

```bash
# 已全局安装
npm list -g stock-sdk-mcp  # → stock-sdk-mcp@0.2.0
which stock-mcp             # → /home/pebynn/.hermes/node/bin/stock-mcp

# 底层库路径
ls /home/pebynn/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules/stock-sdk/
# → dist/index.cjs (CJS), dist/index.js (ESM)
```

## Python 调用模式

collect_data.py 不能直接 import stock-sdk（它是 Node.js 模块）。
标准模式：subprocess 调 Node.js 一次性获取所有数据，输出 JSON。

```python
import subprocess, json

STOCK_SDK_NODE = '/home/pebynn/.hermes/node/bin/node'  # 或直接用 'node'
NODE_PATH = '/home/pebynn/.hermes/node/lib/node_modules'
SDK_CJS = '/home/pebynn/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules/stock-sdk/dist/index.cjs'

def collect_via_stock_sdk():
    """调用 stock-sdk 获取所有写作管线数据"""
    code = f"""
    const {{default: StockSDK}} = require('{SDK_CJS}');
    const sdk = new StockSDK();
    (async () => {{
        const result = {{}};
        try {{ result.market = await sdk.getMarketOverview(); }} catch(e) {{ result.market_error = e.message; }}
        try {{ result.industries = await sdk.getIndustryList(); }} catch(e) {{ result.industries_error = e.message; }}
        try {{ result.concepts = await sdk.getConceptList(); }} catch(e) {{ result.concepts_error = e.message; }}
        try {{ result.fundFlow = await sdk.getMarketFundFlow(); }} catch(e) {{ result.fundFlow_error = e.message; }}
        try {{ result.fundRank = await sdk.getFundFlowRank({{scope:'sector'}}); }} catch(e) {{ result.fundRank_error = e.message; }}
        try {{ result.zt = await sdk.getZTPool({{type:'zt'}}); }} catch(e) {{ result.zt_error = e.message; }}
        try {{ result.dt = await sdk.getZTPool({{type:'dt'}}); }} catch(e) {{ result.dt_error = e.message; }}
        process.stdout.write(JSON.stringify(result));
    }})();
    """
    env = {{**os.environ, 'NODE_PATH': NODE_PATH}}
    r = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"stock-sdk failed: {r.stderr[:200]}")
    return json.loads(r.stdout)
```

## 数据结构映射

### get_market_overview() → 指数+涨跌家数+北向+涨停家数

```json
{
  "indices": [
    {"code": "sh000001", "name": "上证指数", "price": 3350.0, "changePercent": 0.57, ...},
    {"code": "sz399001", "name": "深证成指", ...},
    {"code": "sz399006", "name": "创业板指", ...},
    {"code": "sh000688", "name": "科创50", ...}
  ],
  "upDownCount": {"up": 2315, "down": 2680},
  "northbound": {"netInflow": 12.3},
  "ztCount": 45,
  "dtCount": 8
}
```

### get_industry_list() → 行业板块（含领涨股）

```json
[
  {"code": "BK1027", "name": "半导体", "changePercent": 3.21, "topStock": "中芯国际", "topStockChange": 5.2},
  ...
]
```

### get_fund_flow_rank({scope:'sector'}) → 行业资金流排行

```json
{
  "stock": [...],
  "sector": [
    {"name": "半导体", "netInflow": 12.5e8, ...},
    ...
  ]
}
```

## 已知坑点

| 坑 | 原因 | 应对 |
|:---|:-----|:-----|
| `TypeError: fetch failed` | 腾讯/东方财富 API 间歇性不可用 | subprocess 加重试（最多2次，间隔3s） |
| 北交所(92/83开头)无数据 | 腾讯源不支持北交所 | 采集时跳过北交所板块/个股 |
| 雪球爬虫被反自动化 | React 事件拦截 | 降级到 Markdown 备份 + 手动发布 |
| stock-sdk volume 单位是"手" | Tencent API 返回原始值 | ×100 转为"股" |
| 单次 subprocess 超时 | 6个维度过重 | 每个维度独立 subprocess，允许部分成功 |

## 集成到 collect_data.py 的插入点

collect_data.py 中 6 个数据采集段，每个前面加 stock-sdk 尝试：

```python
# 示例：板块行情采集，第2节（原 L652-685）
# 在 try ak.stock_board_industry_name_em() 之前插入：
stock_sdk_data = try_stock_sdk_sectors()
if stock_sdk_data:
    data["sectors"]["industry"] = stock_sdk_data
else:
    # 继续原有 AKShare 逻辑
    ...
```

每个段独立尝试，允许部分成功。`data_completeness` 基于实际数据判断。

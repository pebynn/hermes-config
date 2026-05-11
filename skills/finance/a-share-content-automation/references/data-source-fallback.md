# AKShare 数据源故障降级策略 (2026-05-08 更新)

## ⚠️ 当前环境 EastMoney 全线封锁

**EastMoney (push2/push2his) IP 永久封锁** — 所有 `ak.stock_*_em()` 端点返回空响应。
这不是晚间黑窗，不会自动恢复。所有 AKShare 东财端点标记为 `DEPRECATED`。

**唯一可行主数据源：stock-sdk（腾讯 qt.gtimg.cn）**
详见 `references/stock-sdk-data-collection.md`。

## 降级链（2026-05-08 更新 — stock-sdk 优先）

| 维度 | stock-sdk 替代 | 二级降级 |
|------|---------------|---------|
| 大盘指数 | `get_market_overview()` | Sina → Xueqiu |
| 板块数据 | `get_industry_list()` / `get_concept_list()` | Sina |
| 主力资金 | `get_market_fund_flow()` | ❌ 无备用 |
| 行业资金流 | `get_fund_flow_rank({scope:'sector'})` | ❌ 无备用 |
| 涨跌停 | `get_zt_pool({type:'zt'/'dt'})` | ❌ 无备用 |
| 涨跌家数 | `get_market_overview()` | ❌ 无备用 |

## 审计铁律：不仅查 SQL

当审计脚本是否需要调整时：
1. 只查 SQL 查询是不够的——脚本可能写死了通过 AKShare 采集
2. 必须 trace 每个数据值到它的最终 API 端点，验证该端点当前是否可用
3. SQL 表里有数据不代表脚本会用——如果采集层已经断了，DB 再新也没用
4. import/require 链 + API 端点 + 网络连通性 三者全都验证

## 故障检测

```bash
# 验证 stock-sdk
NODE_PATH=/home/pebynn/.hermes/node/lib/node_modules \
  node -e "const {default:SDK}=require('/home/pebynn/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules/stock-sdk/dist/index.cjs');(async()=>{const s=new SDK();const m=await s.getMarketOverview();console.log('OK, indices:',m.indices?.length)})()"

# 验证 Sina
curl -s --max-time 5 "https://hq.sinajs.cn/list=sh000001" -H "Referer: https://finance.sina.com.cn"
```

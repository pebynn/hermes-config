# AKShare 晚间 API 黑窗 (19:00-08:00)

## 症状

北京时间 19:00 ~ 次日 08:00，所有 AKShare `_em` 后缀端点（东方财富 push2 API）全部超时：

```
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
curl: (52) Empty reply from server
```

直接 curl 同样失败：
```bash
curl https://push2.eastmoney.com/api/qt/clist/get?...
# → Empty reply from server (TLS handshake OK, no data)
curl https://push2his.eastmoney.com/api/qt/stock/kline/get?...
# → Empty reply from server
```

## 影响范围

所有依赖东方财富 push2 平台的 AKShare 端点：
- `stock_zh_index_daily_em()` — 指数日K线
- `stock_board_industry_name_em()` — 行业板块
- `stock_market_fund_flow()` — 主力资金
- `stock_sector_fund_flow_rank()` — 行业资金流
- `stock_zt_pool_em()` / `stock_zt_pool_dtgc_em()` — 涨跌停
- `stock_zh_a_spot_em()` — 实时行情

东方财富网站 `quote.eastmoney.com` / `data.eastmoney.com` 正常访问（仅 push2 API 服务器关闭）。

## 应对方案

### 1. Sina 备用数据源

Sina 财经 API 全天可用：

| 数据 | Sina 端点 |
|:--|:--|
| 指数实时行情 | `hq.sinajs.cn/list=sh000001,sz399001,...` |
| 行业板块 | `vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData` |
| K线历史 | `money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData` |

⚠️ Sina 字段映射见 `references/sina-api-field-map.md`

### 2. 图表缓存优先

`generate_charts.py` 已实现：图表存在且 >1KB 直接复用，不调用 API。

### 3. Signal alarm 超时

所有图表函数的 AKShare API 调用外包裹 25-30s 超时：
```python
import signal
signal.alarm(25)
df = ak.stock_zh_index_daily_em(symbol="sh000001")
signal.alarm(0)
```

### 4. Cron 不受影响

所有 cron 任务在 15:30-16:00 执行，不在黑窗内。手动晚间测试需使用备用源。

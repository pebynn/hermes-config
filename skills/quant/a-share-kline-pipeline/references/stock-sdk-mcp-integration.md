# stock-sdk-mcp 集成与分析文档

## 安装

已在 `/home/pebynn/.hermes/config.yaml` 添加：
```yaml
mcp_servers:
  stock-sdk:
    command: /home/pebynn/.hermes/node/bin/stock-mcp
    args: []
    timeout: 120
```

bin: `/home/pebynn/.hermes/node/bin/stock-mcp`
npm: `stock-sdk-mcp@0.2.0`
底层数据源: 腾讯 qt.gtimg.cn / ifzq.gtimg.cn

## 可用工具 (50+)

| 类别 | 工具 | 实测 |
|------|------|------|
| 实时行情 | get_a_share_quotes / get_all_a_share_quotes | ✅ |
| | get_hk_quotes / get_us_quotes / get_fund_quotes | ✅ |
| | get_quotes_by_query (模糊搜索) | ✅ |
| 历史K线 | get_history_kline (日/周/月, 含复权) | ✅ 5914行(23年) |
| 分钟K线 | get_minute_kline (1/5/15/30/60分) | ✅ 1205行 |
| 分时图 | get_today_timeline | ✅ |
| 技术指标 | get_kline_with_indicators(MA/MACD/BOLL/KDJ/RSI/WR/BIAS/CCI) | ✅ |
| 板块 | get_industry_list / get_industry_spot | ✅ |
| | get_industry_kline / get_industry_constituents | ✅ 6379行 |
| | get_concept_list / get_concept_kline | ⚠️ 部分成功 |
| 资金流 | get_fund_flow / get_fund_flow_rank | ✅ |
| | get_market_fund_flow / get_sector_fund_flow_history | ✅ |
| 北向 | get_northbound_realtime / get_northbound_history / get_northbound_holding_rank | ✅ |
| 涨停 | get_zt_pool (涨停/昨日涨停/强势/次新/炸板/跌停 6池) | ✅ |
| 龙虎榜 | get_dragon_tiger_list / get_dragon_tiger_stats / get_dragon_tiger_seat_detail | ✅ |
| 大宗 | get_block_trade | ✅ |
| 融资融券 | get_margin_data | ✅ |
| 选股 | scan_market (涨跌幅/量/换手率/PE过滤) | ✅ |
| 大盘 | get_market_overview (指数/板块/涨跌家数/北向) | ✅ |
| 复合 | analyze_stock / compare_stocks | ✅ |
| 期货 | get_futures_kline / get_global_futures_spot / get_global_futures_kline | ✅ |
| 期权 | get_index_option_spot / get_commodity_option_kline | ✅ |
| 日历 | get_trading_calendar (1990至今) | ✅ |
| 分红 | get_dividend_detail | ✅ |

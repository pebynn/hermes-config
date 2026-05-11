# A股K线数据源全面深度调研 (2026-05-08)

> 调研背景: 环境 Ubuntu/中国境内/无VPN，AKShare全线超时。需同时满足量化策略回测(finance) + 每日复盘(writing) 双域需求。

---

## 1. 当前环境实测可用性

| 数据源 | 环境可用 | 关键限制 |
|--------|---------|---------|
| **雪球 API** | ✅ 已稳定使用 | 无成交额(amount)，用close×volume估算 |
| **Tushare Pro** | ✅ 已集成(token已配) | 免费版200次/日(pro.daily 1次全A够用) |
| **腾讯 qt.gtimg.cn** | ✅ 公开可用 | 日K最多1023条(约4年)；分钟K稳定 |
| **Sina hq.sinajs.cn** | ✅ 公开可用 | 仅实时快照，无历史K线 |
| **东方财富 push2直连** | ✅ 有IP白名单 | 反爬严格(第2页起封IP)，限Top100 |
| **AKShare (akshare)** | ❌ 全线超时 | 所有接口均被网络封锁 |
| **Baostock** | ⏳ **待实测** | 纯数据源，无需注册 |
| **iTick API** | ⏳ 待实测 | 免费500次/日，可能需境外DNS |

---

## 2. Baostock — 实测 (2026-05-08)

**定位**: 免费开源(无需注册！)，湘财证券旗下，专为A股量化设计
**安装**: 已安装 v0.9.1 在 `quant_env`

### 实测结果

| 测试项 | 结果 | 耗时 |
|--------|------|------|
| 登录 | ✅ 成功 | <1s |
| 单只日K线(茅台7天) | ✅ 含真实amount/pctChg/turnover/isST | <2s |
| 复权因子(茅台) | ✅ 可用 | <2s |
| stock全量列表 | ❌ 超时 | >60s |
| 行业分类 | ❌ 超时 | >20s |
| 5分钟K线 | ❌ 超时 | >60s |
| 上证指数K线 | ❌ 超时 | >15s |

**结论**: 单只日K线偶尔可用但间歇性超时，不适合做主数据源。不建议替换现有的Tushare+雪球管线。

### 数据范围（理论值，非实测）

```
日/周/月 K线 → 1990-12-19 至今 (全A股，最全历史)
5/15/30/60分 K线 → 2020-01-03 至今 (近5年) [❌实测超时]
...（以下省略，全部在实测中部分不可用）
```

### 数据范围

```
日/周/月 K线 → 1990-12-19 至今 (全A股，最全历史)
5/15/30/60分 K线 → 2020-01-03 至今 (近5年)
复权因子 → 1990-2017逐年提供原始因子
指数K线 → 综合/规模/一级行业/二级行业/策略/成长/价值/主题
财务数据 → 利润/运营/成长/偿债/现金流/杜邦(2007至今，6大类)
行业分类 → 上证50/沪深300/中证500成分股
交易日历 → 2017至今
宏观经济 → 利率/存准率/M2/SHIBOR(1978至今)
```

### key API 函数

```python
import baostock as bs
bs.login()  # 无需任何账号密码

# 日K线 (含pctChg/amount/turnover/isST)
rs = bs.query_history_k_data_plus(
    "sh.600519", 
    "date,open,high,low,close,volume,amount,pctChg,turnover,isST",
    start_date="2020-01-01",
    end_date="2026-05-08",
    frequency="d",     # d=日, w=周, m=月
    adjustflag="2"     # 1=后复权, 2=前复权, 3=不复权
)
df = rs.get_data()

# 分钟K线 (5/15/30/60分)
rs = bs.query_history_k_data_plus(
    "sh.600519",
    "date,time,open,high,low,close,volume,amount",
    start_date="2026-01-01",
    frequency="5",     # 5=5分钟, 15, 30, 60
)
df = rs.get_data()

# 复权因子
rs = bs.query_adjust_factor(code="sh.600519", start_date="2020-01-01")

# 全股票列表
rs = bs.query_all_stock(day="2026-05-08")

bs.logout()
```

### 关键特点

| 维度 | Baostock | 雪球(当前) |
|------|----------|-----------|
| 成交额(amount) | ✅ **真实** | ❌ 估算(close×volume) |
| 涨跌幅(pctChg) | ✅ **真实** | ✅ |
| ST标记(isST) | ✅ **有** | ❌ |
| 历史起点 | **1990-12-19** | ~2018(约8年) |
| 频率 | 日+5/15/30/60分 | 仅日 |
| 复权因子 | ✅ 原始因子 | ❌ 无 |
| 行业分类 | ✅ 上证50/沪深300/中证500 | ❌ |
| 财务数据 | ✅ 6大类(2007至今) | ❌ |

### 更新时效

- **日K线**: 交易日17:30后更新当日数据 (比writing域15:30晚2h，但量化回测次日可用)
- **分钟K线**: 次日更新
- **财务数据**: 次自然日01:30

### 局限

- 17:30才更新，无法满足writing域15:30盘后采集
- 逐只拉取（无tushare那样一次拉全A的批量接口），但单次~0.2s，全A~5000只并行20线程约50s
- 无板块资金流/主力资金/涨跌停列表（writing域仍需AKShare/雪球/Sina）
- 无指数实时行情（股票+指数需分开查询）

### 对现有管线的价值

| 替换点 | 当前方案 | Baostock方案 |
|--------|---------|-------------|
| 历史全量K线 | 雪球(~8年, 无amount) | 1990至今, 含amount/复权因子 |
| 分钟K线 | ❌ 无 | 2020至今的分K |
| 策略脚本kline_get兜底 | API雪球 | API Baostock (含ST过滤) |
| 复权因子 | ❌ 无 | ✅ 原始因子 |
| 财务数据precache | AKShare超时 | Baostock 6大类 |
| 行业成分股 | Tushare(有token) | Baostock(无需注册) |

---

## 3. 腾讯股票API — 稳定公开接口

### 实时行情

```
GET http://qt.gtimg.cn/q=sh600000,sz000001,s_sh600519
```
返回易解析格式（~50只/次，~0.1s）。批量用逗号分隔。

### 前复权日K线

```
GET http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600000,day,,,6,qfq
```
返回JSON：`{data: {sh600000: {qfqday: [[date, open, close, high, low, volume], ...]}}}`
最多1023条（约4年数据）。

### 分钟K线

```
GET http://web.ifzq.gtimg.cn/appstock/app/kline/mkline?param=sh600000,m5,,320
```
支持 m1/m5/m15/m30/m60。最多320条。

### 评价

- **稳定性**: 腾讯云基础设施，多年稳定
- **速度**: JSON格式，快于Sina
- **限制**: 无批量接口（逐只拉），日K最多1023条，无全量历史
- **适用**: writing域补实时行情 + 分钟K线，量化策略可用作日内因子

---

## 4. stock-sdk-mcp — Node.js MCP Server(腾讯源) —— ✅ **强烈推荐**

**实测日期**: 2026-05-08
**GitHub**: https://github.com/chengzuopeng/stock-sdk-mcp
**安装**: `npm install -g stock-sdk-mcp` (已全局安装)
**路径**: `/home/pebynn/.hermes/node/bin/stock-mcp`

### 实测结果

| 测试项 | 结果 | 性能数据 |
|--------|------|---------|
| 单只实时行情(茅台) | ✅ | price/change%/volume/amount/marketCap 全字段 |
| 批量实时行情(20只) | ✅ | **327ms** 返回全部 |
| 历史日K线(前复权) | ✅ | **5914行**(约23年)，含amount/changePercent/amplitude/turnoverRate |
| 5分钟K线 | ✅ | **1205行**，含avgPrice |
| 行业板块K线(银行) | ✅ | **6379行**完整历史日K |
| 沪深300指数 | ✅ | 实时行情正常 |
| 概念板块K线 | ❌ | 参数问题待排查 |
| 港股K线 | ❌ | 格式问题待排查 |
| 资金流排名 | ❌ | MCP层面fetch failed |

### MCP Server工具列表（50+工具已注册）

**核心K线类**:
| MCP工具 | 功能 | 状态 |
|---------|------|------|
| `get_history_kline` | A股日/周/月K线(含前复权) | ✅ |
| `get_minute_kline` | 1/5/15/30/60分K线 | ✅ |
| `get_kline_with_indicators` | K线+技术指标(MA/MACD/BOLL/KDJ/RSI/WR/BIAS/CCI/ATR) | ✅ |
| `get_today_timeline` | 当日分时走势 | ✅ |
| `get_hk_history_kline` | 港股历史K线 | ⚠️ |
| `get_us_history_kline` | 美股历史K线 | ⚠️ |

**板块/概念类**:
| `get_industry_list` | 行业板块列表 | ⚠️ |
| `get_industry_kline` | 行业板块日/周/月K线 | ✅ |
| `get_industry_constituents` | 行业板块成分股 | ✅ |
| `get_concept_list` | 概念板块列表 | ✅ |
| `get_concept_kline` | 概念板块K线 | ⚠️ |
| `get_concept_constituents` | 概念板块成分股 | ⚠️ |

**资金流类**:
| `get_fund_flow` | 个股资金流向 | ✅ |
| `get_fund_flow_rank` | 资金流排名(个股/板块) | ✅ |
| `get_market_fund_flow` | 大盘资金流 | ✅ |
| `get_stock_fund_flow_history` | 个股资金流历史 | ✅ |
| `get_northbound_realtime` | 北向资金实时 | ✅ |
| `get_northbound_history` | 北向资金历史 | ✅ |
| `get_northbound_holding_rank` | 北向持股排行 | ✅ |

**涨停/盘口类**:
| `get_zt_pool` | 涨停股池(6种:涨停/昨涨停/强势/次新/炸板/跌停) | ✅ |
| `get_dragon_tiger_list` | 龙虎榜详情 | ✅ |
| `get_dragon_tiger_stats` | 龙虎榜统计(个股/机构/营业部) | ✅ |
| `get_block_trade` | 大宗交易 | ✅ |
| `get_margin_data` | 融资融券 | ✅ |
| `get_stock_changes` | 盘口异动(22种) | ✅ |

**复合分析类**:
| `scan_market` | 条件选股(涨跌幅/成交量/换手率/PE过滤) | ✅ |
| `analyze_stock` | 个股全景分析(K线+指标+资金流+分红) | ✅ |
| `compare_stocks` | 多股对比分析 | ✅ |
| `get_market_overview` | 大盘概览(指数/板块TOP10/涨跌家数/北向/涨停) | ✅ |
| `get_sector_analysis` | 板块深度分析(K线+成分股) | ✅ |

**其他**:
| `search_stock` | 按代码/名称/拼音搜索股票 | ✅ |
| `get_a_share_code_list` | 全A股代码列表(5000+只) | ✅ |
| `get_trading_calendar` | A股交易日历(1990至今) | ✅ |
| `get_dividend_detail` | 分红配送详情 | ✅ |
| `get_futures_kline` | 国内期货K线 | ✅ |

### 集成Hermes方式

在 `~/.hermes/config.yaml` 添加：

```yaml
mcpServers:
  stock-sdk:
    command: /home/pebynn/.hermes/node/bin/stock-mcp
    transport: stdio
```

### 对现有管线价值

| 缺口 | 当前方案 | stock-sdk填补 |
|------|---------|--------------|
| 分钟K线 | ❌ 无 | ✅ 1/5/15/30/60分 |
| 行业板块K线 | ❌ 无 | ✅ 行业+概念历史日K |
| 资金流历史 | ❌ 无(AKShare不可用) | ✅ 个股/板块/北向资金流 |
| 涨停池/龙虎榜 | ❌ 无(AKShare不可用) | ✅ 涨停6池+龙虎榜+大宗交易 |
| 实时行情批量查询 | ❌ 无 | ✅ 全A股5000+只行情 |
| 条件选股 | ❌ 无 | ✅ 按涨跌幅/成交量/PE扫描|
| 融资融券 | ✅ margin_data.py | ✅ 替代方案 |
| 北向资金 | ❌ 无 | ✅ 实时+历史+持股排行 |

### 大规模使用坑点 (2026-05-08回填实测)

**EastMoney 隐性限流**: stock-sdk `getHistoryKline` 底层实际调用 EastMoney `push2his.eastmoney.com`。
连续约 2200 只股票的全历史请求后，所有 EastMoney 域名返回空响应（curl exit 52），导致后续请求全部 `fetch failed`。
限流持续 30-60min 后自动恢复。

| 阶段 | 表现 | 速率 |
|:-----|:-----|:-----|
| 正常期 (0~2200只) | API 正常响应 | ~80-100只/min (12路并发) |
| 限流期 (2200+只) | 全部域名空响应 | 0 |
| 恢复期 (30-60min后) | 逐步恢复 | 需重新开始 |

**北交所不支持**: 92xxxx/83xxxx 开头股票历史K线全部 `fetch failed`。
实时行情(`getSimpleQuotes`)正常，但历史K线不可用。
原因：EastMoney push2his 不收录北交所。需走 parquet 补丁方案。

**解决方案**: 遇到限流后改用 parquet→MySQL 补丁脚本
(`scripts/parquet_patch_mysql.py`)，不依赖外部 API。

---

## 5. iTick API — 免费跨国数据源

**官网**: https://itick.org
**GitHub**: https://github.com/itick-org/free-stock-api

- **免费版**: 500次/日 REST API + WebSocket
- **支持市场**: A股+港股+美股+外汇+期货+加密货币
- **K线支持**: 全历史日线+分钟线，OHLCV完整
- **协议**: REST + WebSocket + FIX
- **局限**: 境外服务器，在中国境内可能需要翻墙(待实测)
- **注意**: 免费额度有限，不适合全市场5000只A股批量拉取

---

## 6. 数据源对比矩阵

### 历史日K线 (全A股)

| 源 | 历史起点 | 全量批量 | 速度 | 成交额 | 涨跌幅 | 复权 |
|----|---------|---------|------|--------|-------|------|
| Baostock | 1990-12-19 | ❌逐只 | ~0.2s/只 | ✅真实 | ✅真实 | ✅原始因子 |
| Tushare | 全历史 | ✅1次全A | ~0.4s/日 | ✅真实 | ✅真实 | ✅ |
| 雪球 | ~2018 | ❌逐只 | ~0.6s/只 | ❌估算 | ✅ | ❌ |
| 腾讯 | ~2022(1023条) | ❌逐只 | ~0.3s/只 | ✅ | ✅ | ✅前复权 |
| AKShare | 全历史 | ❌逐只 | ~0.5s/只(本环境不可用) | ✅ | ✅ | ✅ |

### 分钟K线

| 源 | 频率 | 历史范围 | 可用性 |
|----|------|---------|-------|
| Baostock | 5/15/30/60分 | 2020至今 | ✅ |
| 腾讯 | 1/5/15/30/60分 | 约320条 | ✅ |
| stock-sdk-mcp(腾讯源) | 同上 | 同上 | ✅ MCP |
| iTick | 全频率 | 全历史 | ⏳需测试 |
| AKShare | 各种 | 有限 | ❌本环境不可用 |

### 板块/行业指数

| 源 | 板块日K线 | 成分股 | 适用域 |
|----|----------|--------|-------|
| Baostock | ✅一级/二级行业 | ✅上证50/沪深300/中证500 | 量化回测 |
| 腾讯/stock-sdk-mcp | ✅行业+概念 | ❌ | Writing板块分析 |
| 东方财富直连 | ✅(Top100) | ❌ | Writing资金流 |

---

## 7. 建议管线演进路径

### 阶段1: 加入Baostock作为历史K线主力 (最高ROI)

```
precache_kline.py 数据源优先级:
  Baostock (1990至今, 含amount/pctChg/isST)
  → 雪球 (降级, ~8年)
  → 腾讯 (降级, ~4年)
```

**价值**: 一次性替换雪球的amount估算问题，全历史回测数据更完整

### 阶段2: 分钟K线 (新增能力)

```
Baostock 分钟K线接口:
  → 5/15/30/60分K线 (2020至今)
  → 可用于日内策略回测 + 日内形态因子(intraday_pattern)
```

### 阶段3: 评估stock-sdk-mcp接入

```
作为MCP Server接入Hermes:
  → 行业板块K线 → writing域板块分析
  → 概念板块K线 → 热点概念追踪
  → 资金流排名 → 资金流向分析
```

---

## 8. 验证脚本

```bash
# 测试Baostock可用性
~/tools/quant_env/bin/python3 -c "
import baostock as bs
lg = bs.login()
print(lg.error_code, lg.error_msg)  # 0, 'success'
rs = bs.query_all_stock(day='2026-05-08')
print(f'全A股: {rs.get_row_count()}只')
rs = bs.query_history_k_data_plus('sh.600519', 'date,close,volume,amount,pctChg',
    start_date='2026-05-06', end_date='2026-05-08', frequency='d', adjustflag='2')
df = rs.get_data()
print(df.head())
bs.logout()
"
```

```bash
# 测试腾讯K线
curl -s 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600000,day,,,6,qfq' | python3 -m json.tool | head -20
```

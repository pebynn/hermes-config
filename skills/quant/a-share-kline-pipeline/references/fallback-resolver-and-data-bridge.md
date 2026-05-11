# 晚间感知三源回退设计

## 模块: `~/quant/fallback_resolver.py`

统一回退引擎,为晚间写作脚本(盘前早报/复盘等)提供数据获取能力。

### 回退链

```
AKShare → Sina → Xueqiu → 本地缓存
```

### 晚间感知

`is_evening()` 判断当前是否为 19:00-08:00 CST(AKShare push2 API黑窗期)。晚间自动跳过AKShare直达Sina/雪球,避免30s×N的超时累积。

`resolve_source()` 返回当前最优数据源名称,供调用方日志标记。

### 接口

| 函数 | 返回 | 说明 |
|:-----|:-----|:-----|
| `get_index(name, date=None)` | dict | 指数日K线(含60日kline列表), source字段标记来源 |
| `get_kline(code, date=None)` | dict | 个股日K线(含60日kline列表), source字段标记来源 |
| `get_index_snapshot(name)` | dict | 指数快照(单行,不含kline列表) |
| `get_all_indices(date=None)` | dict | 批量获取4大指数(sh/sz/cyb/kc50) |
| `is_evening()` | bool | 晚间判断 |
| `resolve_source()` | str | 当前最优源: akshare/sina/xueqiu/cache |

### 数据源实现

**AKShare** (rank 1, 白间优先):
- 指数: 复用 `data_common.get_index_daily()`
- 个股: `ak.stock_zh_a_hist(period="daily", adjust="qfq")`

**Sina** (rank 2, 24h可用):
- K线: `money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`
- 代码格式: `sh600519`(沪市), `sz000858`(深市)
- 需HTTP Session(含重试: 2次, backoff 0.5s)

**Xueqiu** (rank 3, 需cookie):
- 通过 `kline_fallback.py` 调用 `xueqiu_kline.py`
- 代码格式: `SH600519`, `SZ000858`
- Cookie路径: `~/.hermes/credentials/xueqiu_cookies.json`

**本地缓存** (rank 4, 最终兜底):
- 读取 `~/.finquant/cache/kline/{code}.parquet`
- 列: 日期/开盘/收盘/最高/最低/成交量/成交额/振幅/涨跌幅/涨跌额/换手率

### 返回结构

所有接口返回统一的dict结构:
```python
{
    "symbol": "sh000001",
    "name": "上证指数",
    "date": "2026-05-08",
    "open": 3456.78,
    "close": 3421.34,
    "high": 3470.12,
    "low": 3408.90,
    "volume": 234567890,
    "pct_chg": -0.85,
    "source": "sina",  # 标记实际数据源
    "kline": [{date, open, close, high, low, volume}, ...]  # 最近60日
}
```

### 晚间使用示例

```python
from fallback_resolver import get_all_indices, get_kline, is_evening

if is_evening():
    print("晚间模式: AKShare不可用,自动走Sina/雪球回退")

indices = get_all_indices()
for code, data in indices.items():
    print(f"{data['name']}: {data['close']} ({data['pct_chg']:+.2f}%) [{data['source']}]")

stock = get_kline("600519")
if stock:
    print(f"贵州茅台: {stock['close']} source={stock['source']}")
```

## 模块: `~/quant/data_bridge.py`

量化→写作单向只读数据桥,为晚间写作脚本(`morning_brief`/复盘/日报)提供量化信号读取。

### 接口

| 函数 | 返回 | 数据源 |
|:-----|:-----|:-----|
| `get_daily_signals(date=None)` | list[dict] | MySQL `daily_signal_detail`, 当日无数据自动回退最近交易日 |
| `get_top_stocks(n=20)` | list[dict] | JSON优先(`/tmp/midcap_signal.json`,>24h过期)→MySQL回退 |
| `get_market_summary(date=None)` | dict | 综合: MySQL信号+parquet指数+涨跌停统计+成交额 |

### MySQL连接

- host: 127.0.0.1, user: stock, password: `***`(字面值), db: stock_kline
- 连接惰性初始化,失败返回空列表不抛异常
- 使用 `pymysql.cursors.DictCursor` 返回dict格式
- date/datetime/Decimal 类型自动转为字符串/float

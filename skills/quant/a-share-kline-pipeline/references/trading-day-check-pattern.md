# A股交易日判断模式 — 可复用参考

## 动机

多数A股数据拉取 cron job 用 `* * 1-5` 限制工作日执行，但中国节假日（春节/五一/国庆/清明/端午/中秋）仍会触发无效拉取，浪费API配额和成本。

解决方案：在每个数据拉取脚本中加入 `is_trading_day()` 预检查，通过交易日历缓存精确判断。

## 实现 (Python + AKShare)

```python
from pathlib import Path
from datetime import date
from typing import Optional

def is_trading_day(d: Optional[date] = None) -> bool:
    """
    检查指定日期是否为A股交易日。
    首次调用会拉取新浪交易日历并缓存，后续调用直接读缓存。
    """
    if d is None:
        d = date.today()

    CALENDAR_CACHE = Path.home() / ".finquant" / "cache" / "trade_calendar.parquet"

    # 读缓存
    if CALENDAR_CACHE.exists():
        try:
            import pandas as pd
            cal_df = pd.read_parquet(CALENDAR_CACHE)
            trade_dates = set(cal_df["trade_date"].astype(str).values)
            return d.strftime("%Y-%m-%d") in trade_dates
        except Exception:
            pass  # 缓存损坏则重新拉取

    # 拉取交易日历
    try:
        import akshare as ak
        import pandas as pd
        cal_df = ak.tool_trade_date_hist_sina()
        if cal_df is not None and not cal_df.empty:
            CALENDAR_CACHE.parent.mkdir(parents=True, exist_ok=True)
            cal_df.to_parquet(CALENDAR_CACHE, index=False)
            trade_dates = set(cal_df["trade_date"].astype(str).values)
            return d.strftime("%Y-%m-%d") in trade_dates
    except Exception:
        pass

    # 兜底：无法判断时默认继续执行（避免漏拉）
    return True
```

## 在拉取函数中使用

```python
def fetch_and_cache_today() -> bool:
    if not is_trading_day():
        print(f"非交易日，跳过")
        return False

    # ... 正常拉取逻辑
```

## 关键设计决策

| 决策 | 理由 |
|:-----|:-----|
| 缓存到 parquet | 交易日历 8797 行稳定不变，一次拉取终生复用 |
| 缓存不可用时兜底返回 True | 宁可多拉一次也不漏数据 |
| 用 `tool_trade_date_hist_sina` 而非自建规则 | 新浪日历覆盖 1990-至今，含调休和临时休市 |
| 缓存目录用 `.finquant/cache/` 而非 `/tmp` | 持久化，跨重启不丢失 |

## 日历覆盖范围

- 数据源: `ak.tool_trade_date_hist_sina()`
- 范围: 1990-12-19 ~ 2026-12-31
- 总交易日: 8797 天
- 包含调休和临时休市信息

## 已应用此模式的文件

- `~/quant/margin_data.py` — 两融数据拉取 (`fetch_and_cache_today()`)
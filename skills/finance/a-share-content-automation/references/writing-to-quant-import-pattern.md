# Writing域 → quant库 跨域导入规范

## 背景 (2026-05-08)

P1-1 任务将 3 个 witing-domain 脚本 (`collect_data.py`, `morning_brief.py`, `weekly_summary.py`)
的 AKShare 直接调用改为通过 `~/quant/data_common.py` 统一数据层调用。

## 导入模式

所有 writing-domain 脚本如需调用 `~/quant/` 下的共享模块，使用以下标准模板：

```python
import sys
from pathlib import Path

QUANT_DIR = str(Path.home() / "quant")
if QUANT_DIR not in sys.path:
    sys.path.insert(0, QUANT_DIR)

try:
    from data_common import get_index_daily, get_sector_flow, get_limit_up_pool, get_trading_calendar
except ImportError:
    # 优雅降级：data_common 不可用时返回空值，不阻断脚本
    def get_index_daily(name='sh000001', start=None, end=None): return None
    def get_sector_flow(date=None): return None
    def get_limit_up_pool(date=None): return {"limit_up": None, "limit_down": None}
    def get_trading_calendar():
        import pandas as pd
        return pd.DataFrame()
```

## 关键原则

1. **`sys.path.insert(0, ...)` 而非环境变量** — 零配置，cron/手动运行一致
2. **try/except ImportError 兜底** — data_common 不可用时脚本不崩溃，返回空值
3. **保留 AKShare 直接引用作为兜底** — 尚未迁移到 data_common 的接口仍可直接 `import akshare as ak`
4. **日志来源标注更新** — `_meta.sources` 字段标明 `data_common.xxx` 而非裸 `AKShare xxx`

## 已迁移的 AKShare 调用

| 原 AKShare 调用 | data_common 函数 | 使用脚本 |
|:--|:--|:--|
| `ak.stock_zh_index_daily_em(symbol=...)` | `get_index_daily(name=...)` | collect_data.py |
| `ak.stock_sector_fund_flow_rank(...)` | `get_sector_flow(date=...)` | collect_data.py |
| `ak.stock_zt_pool_em(date=...)` | `get_limit_up_pool(date=...)["limit_up"]` | collect_data.py |
| `ak.stock_zt_pool_dtgc_em(date=...)` | `get_limit_up_pool(date=...)["limit_down"]` | collect_data.py |
| `ak.tool_trade_date_hist_sina()` | `get_trading_calendar()` | collect_data.py, morning_brief.py, weekly_summary.py |

## 未迁移的 AKShare 调用（保留直接引用）

以下接口仍由各脚本直接 `import akshare as ak` 调用，因不在 data_common 覆盖范围内：

| 接口 | 用途 | 脚本 |
|:--|:--|:--|
| `ak.stock_board_industry_name_em()` / `ak.stock_board_concept_name_em()` | 板块列表 | collect_data.py |
| `ak.stock_market_fund_flow()` | 主力资金流 | collect_data.py |
| `ak.stock_zh_updown_statistics()` | 涨跌家数 | collect_data.py |
| `ak.index_us_stock_sina()` | 美股指数(隔夜) | morning_brief.py |
| `ak.futures_foreign_hist(symbol="XIN")` | A50期货 | morning_brief.py |
| `ak.stock_hk_index_daily_sina(symbol="HSI")` | 恒生指数 | morning_brief.py |
| `ak.stock_news_em()` | 财经新闻 | morning_brief.py |

## data_common 新增函数特性

所有新增函数遵循 data_common 统一约定：
- 失败返回 `None` / 空 DataFrame（不抛异常）
- 日志通过 `_log()` 输出到 stderr
- 支持 `ImportError` 兜底
- 详见 `~/quant/data_common.py` 第 824-950 行

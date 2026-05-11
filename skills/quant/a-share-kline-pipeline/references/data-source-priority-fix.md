# precache_kline.py 数据源优先级修正

## 问题

`precache_kline.py` 的 `_fetch_kline()` 三源切换中，数据源1 `stock_zh_a_hist_tx`（腾讯精简版）只返回6列：
`date, open, close, high, low, amount`

而旧版代码为缺失的5列硬编码填0：
```python
df["成交量"] = 0
df["振幅"] = 0.0
df["涨跌幅"] = 0.0
df["涨跌额"] = 0.0
df["换手率"] = 0.0
```

导致所有通过该数据源拉取的K线，成交量/振幅/涨跌幅/换手率全部为0。

## 修复（2026-04-30）

交换数据源优先级：

| 旧版 | 新版 |
|:----|:----|
| 数据源1: `stock_zh_a_hist_tx`（6列，缺成交量） | 数据源1: `stock_zh_a_daily`（9列，含volume/turnover） |
| 数据源2: `stock_zh_a_daily`（有成交量但作为备选） | 数据源2: `stock_zh_a_hist_tx`（精简版，降为备选） |

`stock_zh_a_daily` 返回列：`date, open, high, low, close, volume, amount, outstanding_share, turnover`

从该数据源可通过以下方式计算缺失列：
- 振幅 = (high - low) / low * 100
- 涨跌幅 = close.pct_change() * 100（相对**前一交易日收盘**，这是正确的涨跌幅定义）
- 涨跌额 = close.diff()
- 换手率 = turnover（直接返回）

## 涨跌幅计算修正（重要）

旧版代码使用 `(close - open) / open * 100` 计算涨跌幅，这是**错误的**——涨跌幅应该是基于前一日收盘价，而不是当日开盘价。

```python
# 错误
涨跌幅 = (close - open) / open * 100

# 正确
涨跌幅 = close.pct_change() * 100  # 首行结果为 NaN，后续 fillna(0.0)
```

新版代码统一使用 `pct_change()` (相对前一交易日的百分比变化)。
单日增量更新（daily_kline_update.py）无法计算涨跌幅（无前值），统一填0.0，由策略脚本在读取时自行补算。

## 整档历史数据修复（2026-04-30）

旧版 `stock_zh_a_hist_tx` 写入的5个零列不仅存在于预缓存管线，还通过 `daily_kline_update.py` 写入 MySQL，导致 DB 中约 4966 只股票的成交量/换手率/振幅字段全部为零。

**操作步骤：**
1. 修正 `_fetch_kline` 数据源优先级（stock_zh_a_daily 优先）
2. 清空 parquet 缓存和 CSV 目录
3. 重拉全市场 K 线缓存（`precache_kline.py --market=all --workers=20`，~22分钟/4966只）
4. 全量导入 MySQL（`bulk_import_to_mysql.py`，~50分钟/6.8M行）
5. 删除当日脏数据（`DELETE FROM kline WHERE trade_date='2026-04-30'`）

## 注意事项

- **策略脚本**（mid_cap_enhanced等）仍然使用 `stock_zh_a_hist_tx` 作为数据源1，因为它们只用到open/close/high/low价格列，不需要成交量
- 两个脚本的 `_fetch_kline()` 数据源优先级不同是合理的，不需要统一
- 修复后需要**清空旧缓存**重新拉取（旧缓存已被脏数据污染）
- 删除旧缓存：`rm -rf ~/.finquant/cache/kline/*.parquet`
- 文件名需统一为`{6位代码}.parquet`，旧的`k_`/`k_sz`/`k_sh`前缀用`normalize_kline_cache.py`处理

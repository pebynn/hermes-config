# Cross-Source Validation Protocol (2026-05-12)

After strategy evolution converges, verify results with an **alternative data source** to rule out MySQL-specific overfitting.

## Protocol

1. Pull kline data from Sina API for 200-500 representative stocks (enough for signal diversity)
2. Modify strategies to support `--source sina` flag (read from parquet instead of MySQL)
3. Run backtest on same period as evolution (or a sample-out period)
4. Compare: directionally consistent? Degradation acceptable?

## 2026-05-12 Results

| Strategy | MySQL (full) | Sina (200 stocks) | Pass? |
|:--|:--|:--|:--|
| A Momentum | 50.4% ann | 99.5% ann | ✅ same direction |
| B Reversal | 74.5% ann | 64.7% ann | ✅ robust |
| C Chan | 129.2% ann | -45% ann | ❌ failed |

Key insight: 200 stocks give C only 8 trades — insufficient sample. Need 500+ for meaningful validation.

## Data Pull Notes

- Sina API: `money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`
- Format: `sh600519` or `sz000858`
- Limit: ~500 data points per call
- 200 stocks with 8 workers takes ~60s
- Full 5000 stocks takes 10-30 minutes with 10 workers
- Use parquet cache to avoid re-pulling

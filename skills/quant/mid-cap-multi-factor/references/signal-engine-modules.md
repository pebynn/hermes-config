# 信号引擎模块 API 参考

三个模块位于 `~/quant/`，纯 pandas/numpy，零外部依赖。

## chan_buy_signal.py (454行) — Layer 2 缠论二买

```python
def detect_chan_buy2(kline_df: pd.DataFrame) -> pd.DataFrame:
    """检测二买信号点，返回 DataFrame (date, signal, price, atr, vol_ratio, pullback_pct, buy1_date, buy1_price)"""

def get_latest_signals(codes: list, kline_dir: str = None) -> pd.DataFrame:
    """批量检测最新信号（最近一个交易日）"""

def compute_macd(close: pd.Series, fast=12, slow=26, signal=9) -> tuple:
    """返回 (DIF, DEA, MACD柱)"""

def compute_atr(df: pd.DataFrame, period=14) -> pd.Series:
    """ATR 计算"""
```

## volume_indicators.py (441行) — Layer 3 量价指标

```python
def compute_all_indicators(kline_df: pd.DataFrame) -> pd.DataFrame:
    """输入 OHLCV，输出附加 OBV/MFI/VWAP/KAMA/POS 列的 DataFrame"""

def compute_obv(df: pd.DataFrame) -> pd.Series:
    """OBV 能量潮 + 背离检测"""

def compute_mfi(df: pd.DataFrame, period=14) -> pd.Series:
    """MFI 资金流量指标 (0-100)"""

def compute_vwap_deviation(df: pd.DataFrame, window=20) -> pd.Series:
    """VWAP 偏离百分比"""

def compute_kama(df: pd.DataFrame, er_period=10, fast=2, slow=30) -> pd.Series:
    """KAMA 自适应均线"""

def compute_pos(df: pd.DataFrame, short=5, long=60) -> pd.Series:
    """POS 价格震荡"""
```

## signal_engine.py (895行) — 三层信号合成引擎

```python
def scan_signals(
    market: str = "all",
    mc_min: float = 50e8,
    mc_max: float = 400e8,
    code_filter: Optional[list[str]] = None,
    start_date: str = "2024-07-01",
) -> pd.DataFrame:
    """扫描全池，返回有信号的股票及 L1+L2+L3 得分"""

def today_signal() -> pd.DataFrame:
    """alias: scan_signals(market='all', mc_min=50e8, mc_max=400e8)"""
```

## daily_signal_report.py (251行) — 每日报告生成

```bash
# 全市场扫描 + 格式化为微信推送文本
~/tools/quant_env/bin/python3 ~/quant/daily_signal_report.py
```

## 性能参考

| 配置 | 股票数 | 耗时 |
|:-----|:------|:-----|
| 10只(code_filter) | 10 | ~14s |
| 100只(code_filter) | 100 | ~140s |
| 全市场中盘(market=all+市值过滤) | ~2500 | ~8min (4核) |
| 全市场无过滤 | 4966 | ~13min (4核) |

#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
"""
策略共享库 — data_common.py
提供数据库连接和通用工具函数。
"""
import os
import pandas as pd
import numpy as np

from sqlalchemy import create_engine

# ── MySQL 连接 ──────────────────────────────────────────────
_MYSQL_HOST = os.getenv("MYSQL_STOCK_HOST", "127.0.0.1")
_MYSQL_PORT = os.getenv("MYSQL_STOCK_PORT", "3306")
_MYSQL_USER = os.getenv("MYSQL_STOCK_USER", "stock")
_MYSQL_PASSWORD = os.getenv("MYSQL_STOCK_PASSWORD", "")
_MYSQL_DB = os.getenv("MYSQL_STOCK_DB", "stock_kline")

_ENGINE = None


def _get_db_engine():
    """Return SQLAlchemy engine for stock_kline database (singleton)."""
    global _ENGINE
    if _ENGINE is None:
        url = (
            f"mysql+pymysql://{_MYSQL_USER}:{_MYSQL_PASSWORD}@{_MYSQL_HOST}:{_MYSQL_PORT}/{_MYSQL_DB}?charset=utf8mb4"
        )
        _ENGINE = create_engine(url, pool_recycle=3600, pool_pre_ping=True)
    return _ENGINE


# ── 列名映射 ────────────────────────────────────────────────
COLUMN_MAP = {
    "trade_date": "日期", "date": "日期",
    "open": "开盘", "close": "收盘",
    "high": "最高", "low": "最低",
    "volume": "成交量", "amount": "成交额",
}

# ── 通用指标函数 ────────────────────────────────────────────

def _pct_chg(arr, period):
    """周期收益率 (period日前相比)"""
    result = np.full(len(arr), np.nan)
    if len(arr) > period:
        result[period:] = arr[period:] / arr[:-period] - 1
    return result


def _rolling_mean(arr, w):
    return pd.Series(arr).rolling(w, min_periods=w//2).mean().values


def _rolling_std(arr, w):
    return pd.Series(arr).rolling(w, min_periods=w//2).std(ddof=0).values


# ── 路径常量 ────────────────────────────────────────────────
from pathlib import Path

KLINE_DIR = Path.home() / ".finquant" / "cache" / "kline"
_STOCK_LIST_CACHE = Path.home() / ".finquant" / "cache" / "stocks" / "stock_list.parquet"
_SHARE_DB_CACHE = Path.home() / ".finquant" / "cache" / "shares" / "share_db.parquet"


# ── 股票列表 ────────────────────────────────────────────────

def get_stock_list(market="all"):
    """获取A股股票列表，含市场分类和行业。

    Args:
        market: "all" | "main"(主板) | "gem"(创业板) | "star"(科创板)
    Returns:
        DataFrame with columns: code, name, market, industry, list_date, ...
        失败时返回仅含code列的最小DataFrame(回退到CSV)
    """
    try:
        df = pd.read_parquet(_STOCK_LIST_CACHE)
        market_map = {"all": None, "main": "主板", "gem": "创业板", "star": "科创板"}
        target = market_map.get(market)
        if target:
            df = df[df["market"] == target]
        return df.reset_index(drop=True)
    except Exception:
        # 回退到本地CSV
        import sys
        csv_path = Path(__file__).parent / "_stock_codes.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"  [get_stock_list] parquet不可用, 回退到CSV: {len(df)} 只", file=sys.stderr)
            return df
        return pd.DataFrame(columns=["code"])


def load_share_db():
    """加载总股本数据库。

    Returns:
        dict: {code: shares} 或 {} (加载失败时)
    """
    try:
        df = pd.read_parquet(_SHARE_DB_CACHE)
        if "code" in df.columns and "shares" in df.columns:
            return dict(zip(df["code"], df["shares"]))
        return {}
    except Exception:
        return {}


def get_industry_map():
    """获取行业分类映射。

    Returns:
        dict: {code: industry_name} 或 {} (加载失败时)
    """
    try:
        df = pd.read_parquet(_STOCK_LIST_CACHE)
        if "code" in df.columns and "industry" in df.columns:
            return dict(zip(df["code"], df["industry"]))
        return {}
    except Exception:
        return {}


def verify_write(date_str):
    """端到端写入验证：对比MySQL表与Parquet缓存的当日数据量。

    Args:
        date_str: 日期字符串，格式 "YYYYMMDD" 或 "YYYY-MM-DD"
    Returns:
        dict: {status, mysql_count, parquet_count, stock_pool_count, delta, details}
    """
    try:
        if len(date_str) == 8:
            date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        else:
            date_fmt = date_str

        engine = _get_db_engine()
        mysql_count = int(pd.read_sql(
            "SELECT COUNT(*) AS cnt FROM kline WHERE trade_date = %s",
            engine, params=(date_fmt,)
        )["cnt"].iloc[0])

        parquet_count = 0
        for f in KLINE_DIR.glob("*.parquet"):
            try:
                pf = pd.read_parquet(f)
                if len(pf) > 0:
                    last_date = str(pf.iloc[-1, 0])[:10]
                    if last_date == date_fmt:
                        parquet_count += 1
            except Exception:
                pass

        try:
            stock_pool = pd.read_parquet(_STOCK_LIST_CACHE)
            stock_pool_count = len(stock_pool)
        except Exception:
            stock_pool_count = 0

        denom = max(mysql_count, parquet_count, 1)
        delta_pct = round(abs(mysql_count - parquet_count) / denom * 100, 1)

        details = []
        if mysql_count == 0:
            status = "FAIL"
            details.append("MySQL has 0 rows for this date")
        elif delta_pct < 5:
            status = "PASS"
        elif delta_pct < 15:
            status = "WARN"
            details.append(f"MySQL/Parquet mismatch: {delta_pct}%")
        else:
            status = "FAIL"
            details.append(f"Large mismatch: {delta_pct}%")

        engine.dispose()
        return {
            "status": status,
            "mysql_count": mysql_count,
            "parquet_count": parquet_count,
            "stock_pool_count": stock_pool_count,
            "delta": {"mysql_vs_parquet_pct": delta_pct},
            "details": details,
        }
    except Exception as e:
        return {
            "status": "FAIL",
            "mysql_count": 0, "parquet_count": 0, "stock_pool_count": 0,
            "delta": {"mysql_vs_parquet_pct": 0.0},
            "details": [str(e)],
        }


# ── 交易日历 ────────────────────────────────────────────────

def kline_from_db(code: str, start_date: str = "2024-01-01", end_date: str = "") -> pd.DataFrame:
    """从 MySQL 读取指定股票的 K 线数据。"""
    try:
        engine = _get_db_engine()
        if end_date:
            query = (
                "SELECT trade_date, open, close, high, low, volume, amount, "
                "amplitude, pct_chg, `change`, turnover "
                "FROM kline WHERE code = %s AND trade_date >= %s AND trade_date <= %s "
                "ORDER BY trade_date"
            )
            params = (code, start_date, end_date)
        else:
            query = (
                "SELECT trade_date, open, close, high, low, volume, amount, "
                "amplitude, pct_chg, `change`, turnover "
                "FROM kline WHERE code = %s AND trade_date >= %s "
                "ORDER BY trade_date"
            )
            params = (code, start_date)
        df = pd.read_sql(query, engine, params=params)
        if df.empty:
            return None
        df = df.rename(columns=COLUMN_MAP)
        return df
    except Exception:
        return None


def is_trading_day(dt=None):
    """检查是否为A股交易日。通过MySQL查询或API判断。"""
    if dt is None:
        dt = pd.Timestamp.now()
    else:
        dt = pd.Timestamp(dt)
    if dt.dayofweek >= 5:
        return False
    try:
        date_str = dt.strftime("%Y%m%d")
        engine = _get_db_engine()
        result = pd.read_sql(
            "SELECT 1 FROM trading_calendar WHERE trade_date = %s",
            engine, params=(date_str,)
        )
        engine.dispose()
        return len(result) > 0
    except Exception:
        return dt.dayofweek < 5
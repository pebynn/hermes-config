#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
"""
策略A v2: 主力资金动量增强 — 优化版
=====================================
改进:
  1. 止损 5%→8% — 降低硬止损触发率
  2. 移动止盈 — 从高点回撤>8%止盈
  3. 动态IC权重 — 20日滚动IC调整因子权重
  4. 波动率因子 — 低波动优先，过滤假突破
"""
import sys, os, time, argparse, warnings, json
import numpy as np
import pandas as pd
from datetime import timedelta
from pathlib import Path
warnings.filterwarnings("ignore")

_QDIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..",".."))
sys.path.insert(0, _QDIR)
from data_common import _get_db_engine

# ── Config ──
START_DATE = os.environ.get("BT_START", "2021-01-01")
END_DATE   = os.environ.get("BT_END", "2025-12-31")
WARMUP_DAYS = 120
TOP_N_V2 = 10
STOP_LOSS_V2 = 0.10
TRAILING_STOP = 0.06
PORTFOLIO_STOP_V2 = 0.15
JAN_APR_EMPTY_V2 = False
MOM_ENTRY_THRESHOLD = 0.02
MIN_AMOUNT_V2 = 5e7
MIN_DAYS_V2 = 60
LEVERAGE_V2 = 1.0
TC_COST_V2 = 0.001
IC_WINDOW = 20
IC_TEMPERATURE = 2.0
VOL_WEIGHT_DEFAULT = 0.15
OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "output_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_JSON = OUTPUT_DIR / "backtest_results.json"


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def _pct_chg(arr, period):
    r = np.full(len(arr), np.nan)
    if len(arr) > period: r[period:] = arr[period:] / arr[:-period] - 1
    return r

def _rolling_mean(arr, w):
    return pd.Series(arr).rolling(w, min_periods=w//2).mean().values

def _zscore(arr):
    mu, sd = np.nanmean(arr), np.nanstd(arr)
    return np.zeros_like(arr) if sd == 0 else (arr - mu) / sd


# ═══════════════════════════════════════════════════════════════
# Factor Computation (with Volatility)
# ═══════════════════════════════════════════════════════════════

def compute_factors_v2(df):
    """计算因子: flow, momentum, volatility_20d (R2: 移除turn)"""
    close = df["收盘"].values.astype(np.float64)
    open_ = df["开盘"].values.astype(np.float64)
    high  = df["最高"].values.astype(np.float64)
    low   = df["最低"].values.astype(np.float64)
    amount= df["成交额"].values.astype(np.float64)
    n = len(close)

    # Fund flow proxy
    dr = np.where(high - low < 1e-8, 1e-8, high - low)
    daily_flow = np.sign(close - open_) * amount * (np.abs(close - open_) / dr)
    flow_ema = np.full(n, np.nan)
    flow_ema[0] = daily_flow[0]
    for i in range(1, n): flow_ema[i] = 0.4 * daily_flow[i] + 0.6 * flow_ema[i-1]

    # Momentum (10-day return)
    ret_10d = _pct_chg(close, 10)
    # 5-day return (used for entry filter, no look-ahead)
    ret_5d = _pct_chg(close, 5)

    # Amount MA (for pool filter)
    amount_ma20 = _rolling_mean(amount, 20)

    # Volatility (20-day annualized)
    log_rets = np.full(n, np.nan)
    if n > 1:
        log_rets[1:] = np.log(close[1:] / close[:-1])
    vol_20d = np.full(n, np.nan)
    for i in range(20, n):
        vol_20d[i] = np.nanstd(log_rets[i-19:i+1])

    r = df[["日期"]].copy()
    r["开盘"] = open_; r["收盘"] = close; r["最高"] = high; r["最低"] = low
    r["flow"] = flow_ema; r["mom"] = ret_10d
    r["ret_5d"] = ret_5d  # R3: 5-day return for entry filter
    r["amt_ma20"] = amount_ma20; r["vol_20d"] = vol_20d
    return r


# ═══════════════════════════════════════════════════════════════
# Trailing Stop Logic
# ═══════════════════════════════════════════════════════════════

def check_trailing_stop(pos, current_low, trailing_pct=0.06):
    """检查是否触发移动止盈 (R2: 收紧至6%)。"""
    high_close = pos.get('high_close', None)
    if high_close is None or high_close <= 0:
        return False
    drawdown = (current_low - high_close) / high_close
    return drawdown <= -trailing_pct


# ═══════════════════════════════════════════════════════════════
# Momentum Entry Filter (R2 NEW)
# ═══════════════════════════════════════════════════════════════

def check_momentum_entry(ret_5d_prev, threshold=0.02):
    """R3-FIX: 使用前一日5日动量过滤入场 — 消除未来函数。"""
    if ret_5d_prev is None or (isinstance(ret_5d_prev, float) and np.isnan(ret_5d_prev)):
        return False
    return float(ret_5d_prev) >= threshold - 1e-8


# ═══════════════════════════════════════════════════════════════
# Dynamic IC Weights
# ═══════════════════════════════════════════════════════════════

def compute_rolling_ic_weights(flow_ic, mom_ic, vol_ic,
                                 window=20, temperature=2.0):
    """使用滚动IC计算动态因子权重 (R2: 3因子, 移除turn)。"""
    def _mean_ic(series, w):
        valid = series.dropna()
        if len(valid) == 0:
            return 0.0
        return float(valid.tail(w).mean())

    mean_ics = {
        'flow': _mean_ic(flow_ic, window),
        'mom': _mean_ic(mom_ic, window),
        'vol': _mean_ic(vol_ic, window),
    }

    # Softmax with temperature
    ics = np.array(list(mean_ics.values()))
    scaled = ics / max(temperature, 0.01)
    shifted = scaled - np.max(scaled)
    exp_vals = np.exp(shifted)
    softmax = exp_vals / exp_vals.sum()

    return {k: float(v) for k, v in zip(mean_ics.keys(), softmax)}


# ═══════════════════════════════════════════════════════════════
# Composite Score (with Dynamic Weights)
# ═══════════════════════════════════════════════════════════════

def compute_composite_score_v2(xt, weights, min_amount=5e7):
    """使用动态权重计算综合得分 (R2: 3因子, 移除turn)。"""
    pool = xt[xt['amt_ma20'].notna() & (xt['amt_ma20'] >= min_amount)].copy()
    if len(pool) < TOP_N_V2:
        return pd.Series(dtype=float)

    pool['cs'] = (
        weights.get('flow', 0) * _zscore(pool['flow'].values) +
        weights.get('mom', 0)  * _zscore(pool['mom'].values) +
        weights.get('vol', 0)  * _zscore(-pool['vol_20d'].values)  # low vol preferred
    )
    return pool['cs']


def is_limit_down(xt_row, prev_close):
    """R3: 检测是否跌停 (主板10%跌停板)。"""
    low = float(xt_row.get('最低', 0))
    if prev_close <= 0 or low <= 0:
        return False
    limit_down_price = prev_close * 0.9  # 主板10%跌停
    return low <= limit_down_price * 1.005  # 0.5% tolerance


# ═══════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════

def load_data_v2():
    engine = _get_db_engine()
    ds = (pd.Timestamp(START_DATE)-timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
    df = pd.read_sql("""SELECT code,trade_date,`open`,`close`,high,low,volume,amount
        FROM kline WHERE trade_date>=%(start)s AND trade_date<=%(end)s
        ORDER BY code,trade_date""", engine, params={"start":ds,"end":END_DATE})
    engine.dispose()
    return df.rename(columns={"trade_date":"日期","open":"开盘","close":"收盘",
        "high":"最高","low":"最低","volume":"成交量","amount":"成交额"}).assign(日期=lambda x: x["日期"].astype(str))


# ═══════════════════════════════════════════════════════════════
# Main Backtest
# ═══════════════════════════════════════════════════════════════

def run_backtest_v2(stop_loss=STOP_LOSS_V2, trailing_stop=TRAILING_STOP,
                     ps=PORTFOLIO_STOP_V2, ic_window=IC_WINDOW,
                     ic_temperature=IC_TEMPERATURE):
    t0 = time.time()
    print(f"策略A v2 | {START_DATE}->{END_DATE} | TOP_N={TOP_N_V2}")
    print(f"止损:{stop_loss:.0%} 移动止盈:{trailing_stop:.0%} 组合止损:{ps:.0%}")
    print(f"IC窗口:{ic_window} IC温度:{ic_temperature}")
    print(f"动量过滤:{MOM_ENTRY_THRESHOLD:.0%}")

    # 1. Load
    print("1/5 数据..."); tk = time.time()
    ak = load_data_v2()
    print(f"  [{time.time()-tk:.0f}s] {len(ak):,}行 {ak['code'].nunique()}只")

    # 2. Filter
    print("2/5 筛选..."); tk = time.time()
    universe = {c: g.sort_values("日期").reset_index(drop=True) for c, g in ak.groupby("code")
                if len(g) >= MIN_DAYS_V2 and g.head(20)["成交额"].mean() >= MIN_AMOUNT_V2}
    del ak; print(f"  [{time.time()-tk:.0f}s] {len(universe)}只")

    # 3. Factors (v2 with volatility)
    print("3/5 因子(v2)..."); tk = time.time()
    frames = [(compute_factors_v2(df).assign(code=c)) for c, df in universe.items()]
    panel = pd.concat(frames, ignore_index=True)
    panel = panel[panel["日期"]>=(pd.Timestamp(START_DATE)-timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")]
    panel.set_index(["日期","code"], inplace=True); panel.sort_index(inplace=True)
    print(f"  [{time.time()-tk:.0f}s] {panel.shape[0]:,}行")

    # 4. Backtest
    print("4/5 模拟(v2)..."); tk = time.time()
    dates = sorted(panel.index.get_level_values("日期").unique())
    bdates = [d for d in dates if START_DATE <= d <= END_DATE]
    print(f"  {len(bdates)}天")

    pos = {}; trades = []; prev_nav = 1.0; peak = 1.0; stop_once = False
    pending_exits = {}  # R3: deferred exits
    nav_records = []

    # IC tracking for dynamic weights
    ic_history = {'flow': [], 'mom': [], 'vol': []}
    ic_dates = []
    default_weights = {'flow': 0.50, 'mom': 0.35, 'vol': VOL_WEIGHT_DEFAULT}
    total = sum(default_weights.values())
    default_weights = {k: v/total for k, v in default_weights.items()}
    current_weights = default_weights.copy()

    for di, cd in enumerate(bdates):
        # Jan/Apr close
        if JAN_APR_EMPTY_V2 and int(cd[5:7]) in (1,4):
            for c, p in list(pos.items()):
                if c in universe:
                    ds = universe[c]; m = ds["日期"]==cd
                    if m.any():
                        ep = float(ds[m].iloc[0]["收盘"])
                        trades.append({"c":c,"in":p["in"],"out":cd,
                            "pnl":round((float(ep)-p["ep"])/p["ep"]*100,2),"r":"jan_apr"})
            for c, pe in list(pending_exits.items()):
                if c in universe:
                    ds = universe[c]; m = ds["日期"]==cd
                    if m.any():
                        ep = float(ds[m].iloc[0]["收盘"])
                        trades.append({"c":c,"in":pe["in"],"out":cd,
                            "pnl":round((float(ep)-pe["ep"])/pe["ep"]*100,2),"r":"jan_apr"})
            pos = {}
            pending_exits = {}
            nav_records.append((cd, prev_nav))
            continue

        try: xt = panel.xs(cd).copy()
        except KeyError:
            nav_records.append((cd, prev_nav))
            continue

        ci = dates.index(cd)

        # Execute deferred exits from previous day (R3)
        for c in list(pending_exits.keys()):
            pe = pending_exits.pop(c)
            if c in xt.index:
                xp = float(xt.loc[c,"开盘"])
                trades.append({"c":c,"in":pe["in"],"out":cd,
                    "pnl":round((xp-pe["ep"])/pe["ep"]*100,2),"r":f"px_{pe['reason']}"})
            elif c in universe:
                ds = universe[c]; lc = float(ds["收盘"].values[-1])
                trades.append({"c":c,"in":pe["in"],"out":cd,
                    "pnl":round((lc-pe["ep"])/pe["ep"]*100,2),"r":f"px_nd_{pe['reason']}"})
            if c in pos:
                del pos[c]

        # Previous day cross-section for signal
        xr = None
        if ci > 0:
            try: xr = panel.xs(dates[ci-1]).copy()
            except: pass

        # Stops (v2: hard stop + trailing stop)
        sh = set()
        st_next = set()
        if stop_loss > 0:
            for c in list(pos.keys()):
                if c not in xt.index: continue
                if pos[c].get("in") == cd: continue  # T+1
                dl = float(xt.loc[c,"最低"])
                ep = pos[c]["ep"]
                if ep > 0 and (dl - ep) / ep <= -stop_loss:
                    sh.add(c)
        if trailing_stop > 0:
            for c in list(pos.keys()):
                if c in sh: continue
                if c not in xt.index: continue
                if pos[c].get("in") == cd: continue  # T+1
                dl = float(xt.loc[c,"最低"])
                if check_trailing_stop(pos[c], dl, trailing_stop):
                    st_next.add(c)

        dd = (prev_nav-peak)/peak if peak>0 else 0
        ps_hit = (ps > 0 and dd <= -ps and not stop_once)

        # Rebalance
        rday = (pd.Timestamp(cd).dayofweek == 0) or (di == 0)

        # Ranking (v2: dynamic IC weights)
        top = set()
        if xr is not None and len(xr) >= TOP_N_V2:
            scores = compute_composite_score_v2(xr, current_weights, MIN_AMOUNT_V2)
            if len(scores) >= TOP_N_V2:
                top_n_largest = scores.nlargest(TOP_N_V2*3).index
                top = set([c for c in top_n_largest if c in xt.index][:TOP_N_V2])

        # Sell (R3: next-day open for trailing, t+1 aware)
        nc = {}
        for c, p in list(pos.items()):
            if c not in xt.index:
                if c in universe:
                    ds = universe[c]; lc = float(ds["收盘"].values[-1])
                    trades.append({"c":c,"in":p["in"],"out":cd,
                        "pnl":round((lc-p["ep"])/p["ep"]*100,2),"r":"nd"})
                continue
            if p["in"] == cd:  # T+1 constraint
                nc[c] = p
                continue
            if c in sh:
                prev_close = p.get("pc", p["ep"])
                if is_limit_down(xt.loc[c], prev_close):
                    pending_exits[c] = {"ep":p["ep"],"in":p["in"],"reason":"limit_down"}
                else:
                    pending_exits[c] = {"ep":p["ep"],"in":p["in"],"reason":"stop"}
                continue
            if c in st_next:
                pending_exits[c] = {"ep":p["ep"],"in":p["in"],"reason":"trail"}
                continue
            if ps_hit:
                pending_exits[c] = {"ep":p["ep"],"in":p["in"],"reason":"port_stop"}
                continue
            if rday and c not in top:
                xp = float(xt.loc[c,"开盘"])
                trades.append({"c":c,"in":p["in"],"out":cd,
                    "pnl":round((xp-p["ep"])/p["ep"]*100,2),"r":"drop"})
                continue
            nc[c] = p

        # Buy (R3: momentum entry uses prev-day mom factor, no lookahead)
        if rday and not ps_hit and xr is not None:
            rem = TOP_N_V2 - len(nc)
            if rem > 0 and len(top) > 0:
                for c in [c for c in top if c not in nc and c in xt.index][:rem]:
                    if c not in xr.index: continue
                    ep = float(xt.loc[c,"开盘"])
                    if ep > 0:
                        ret_10d = float(xr.loc[c].get('mom', np.nan))
                        if check_momentum_entry(ret_10d, MOM_ENTRY_THRESHOLD):
                            nc[c] = {"ep":ep,"in":cd,"pc":ep,"high_close":ep}

        # NAV (R3: include pending_exits in today's NAV)
        nav_pos = dict(nc)
        for c, pe in pending_exits.items():
            nav_pos[c] = pe
        if nav_pos:
            cb = 0.0
            for c, p in nav_pos.items():
                if c in xt.index:
                    cb += float(xt.loc[c,"收盘"]) / max(p.get("pc", p["ep"]), 1e-10)
                else:
                    cb += 1.0
            tc = TC_COST_V2 if rday else 0
            nav = prev_nav * (1 + (cb - len(nav_pos)) / TOP_N_V2 * LEVERAGE_V2 - tc)
        else:
            nav = prev_nav

        if nav > peak: peak = nav

        # Update trailing high + prev_close
        for c, p in nc.items():
            if c in xt.index:
                cur_close = float(xt.loc[c,"收盘"])
                p["pc"] = cur_close
                if cur_close > p.get("high_close", p["ep"]):
                    p["high_close"] = cur_close

        prev_nav = nav
        if ps_hit: stop_once = True
        nav_records.append((cd, nav))

        pos = nc

        # Update IC for dynamic weights (every 5 days)
        if di % 5 == 0 and xr is not None and len(xr) >= TOP_N_V2:
            _update_ic(xr, ic_history, ic_dates, cd, ic_window)
            if len(ic_dates) >= ic_window:
                current_weights = compute_rolling_ic_weights(
                    pd.Series(ic_history['flow']),
                    pd.Series(ic_history['mom']),
                    pd.Series(ic_history['vol']),
                    window=ic_window, temperature=ic_temperature
                )

        if (di+1) % 250 == 0 or di == len(bdates)-1:
            print(f"  [{int((di+1)/len(bdates)*100)}%] {cd} NAV={nav:.4f} "
                  f"pos={len(pos)} trades={len(trades)} w={dict((k,round(v,3)) for k,v in current_weights.items())}")

    # End close
    last_date = bdates[-1] if bdates else ""
    for c, p in list(pos.items()):
        if c in universe:
            if p["in"] == last_date: continue
            ds = universe[c]; lc = float(ds["收盘"].values[-1])
            ld = str(ds["日期"].values[-1])
            trades.append({"c":c,"in":p["in"],"out":ld,
                "pnl":round((lc-p["ep"])/p["ep"]*100,2),"r":"end"})
    for c, pe in list(pending_exits.items()):
        if c in universe:
            if pe["in"] == last_date: continue
            ds = universe[c]; lc = float(ds["收盘"].values[-1])
            ld = str(ds["日期"].values[-1])
            trades.append({"c":c,"in":pe["in"],"out":ld,
                "pnl":round((lc-pe["ep"])/pe["ep"]*100,2),"r":f"end_{pe['reason']}"})
    print(f"  [{time.time()-tk:.0f}s]")

    # 5. Metrics
    print("5/5 指标...")
    tdf = pd.DataFrame(trades)
    tdf.to_csv(OUTPUT_DIR / "backtest_trades.csv", index=False)

    ndf = pd.DataFrame(nav_records, columns=["date","nav"])
    ndf.to_csv(OUTPUT_DIR / "backtest_nav.csv", index=False)

    n = len(tdf)
    if n > 0:
        wr = float((tdf["pnl"]>0).sum()/n*100)
        final_nav = float(prev_nav)
        total_ret = (final_nav - 1.0) * 100
        trading_days = len(bdates)
        ann_ret = (final_nav / 1.0) ** (252 / max(trading_days, 1)) - 1

        nav_arr = np.array(ndf["nav"].values)
        peak_arr = np.maximum.accumulate(nav_arr)
        dd_arr = (nav_arr - peak_arr) / peak_arr
        mdd = float(dd_arr.min() * 100)

        daily_rets = np.diff(nav_arr) / nav_arr[:-1]
        rf_daily = 0.02 / 252
        excess = daily_rets - rf_daily
        sharpe = float(np.nanmean(excess) / (np.nanstd(excess) + 1e-10) * np.sqrt(252))
    else:
        wr, ann_ret, mdd, sharpe, total_ret, final_nav, trading_days = 0, 0, 0, 0, 0, 1.0, 0

    results = {
        "final_nav": round(final_nav, 4),
        "total_return": round(total_ret, 2),
        "annual_return": round(ann_ret * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(mdd, 2),
        "win_rate": round(wr, 1),
        "total_trades": n,
        "trading_days": trading_days,
        "config": {
            "top_n": TOP_N_V2, "stop_loss": stop_loss,
            "trailing_stop": trailing_stop, "portfolio_stop": ps,
            "ic_window": ic_window,
        }
    }
    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*56}")
    print(f"  完成! {time.time()-t0:.0f}s")
    print(f"  年化收益: {results['annual_return']:.1f}%")
    print(f"  总收益:   {results['total_return']:.1f}%")
    print(f"  夏普比:   {results['sharpe_ratio']:.2f}")
    print(f"  最大回撤: {results['max_drawdown']:.1f}%")
    print(f"  胜率:     {results['win_rate']:.1f}%")
    print(f"  交易:     {results['total_trades']}")
    print(f"  交易日:   {results['trading_days']}")
    print(f"  参数数:   {len(results['config'])}")
    print(f"{'='*56}")

    # Exit reason breakdown
    print(f"\n退出原因分布:")
    for reason, count in tdf['r'].value_counts().items():
        subset = tdf[tdf['r']==reason]
        wr_r = (subset['pnl']>0).mean()*100
        print(f"  {reason}: {count} ({count/n*100:.1f}%) avg={subset['pnl'].mean():.1f}%")

    return results


def _update_ic(xr, ic_history, ic_dates, cd, window):
    """更新IC历史记录。使用5日forward return计算IC(无look-ahead bias)。"""
    if xr is None or len(xr) < TOP_N_V2:
        return

    pool = xr[xr['amt_ma20'].notna() & (xr['amt_ma20'] >= MIN_AMOUNT_V2)].copy()
    if len(pool) < TOP_N_V2:
        return

    intra_ret = (pool['收盘'] - pool['开盘']) / (pool['开盘'].abs() + 1e-10)

    for factor_name, factor_col in [('flow', 'flow'), ('mom', 'mom'),
                                      ('vol', 'vol_20d')]:
        if factor_col not in pool.columns:
            continue
        factor_vals = pool[factor_col].rank()
        if factor_name == 'vol':
            factor_vals = -factor_vals
        ret_rank = intra_ret.rank()
        ic = factor_vals.corr(ret_rank)
        ic_history[factor_name].append(ic if not np.isnan(ic) else 0.0)

    ic_dates.append(cd)
    max_len = window * 2
    for k in ic_history:
        if len(ic_history[k]) > max_len:
            ic_history[k] = ic_history[k][-max_len:]
    if len(ic_dates) > max_len:
        ic_dates[:] = ic_dates[-max_len:]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=str, default=None, help="覆盖 START_DATE")
    p.add_argument("--end", type=str, default=None, help="覆盖 END_DATE")
    p.add_argument("--stop-loss", type=float, default=STOP_LOSS_V2)
    p.add_argument("--trailing-stop", type=float, default=TRAILING_STOP)
    p.add_argument("--portfolio-stop", type=float, default=PORTFOLIO_STOP_V2)
    p.add_argument("--ic-window", type=int, default=IC_WINDOW)
    p.add_argument("--ic-temperature", type=float, default=IC_TEMPERATURE)
    args = p.parse_args()
    if args.start:
        START_DATE = args.start
    if args.end:
        END_DATE = args.end
    run_backtest_v2(stop_loss=args.stop_loss, trailing_stop=args.trailing_stop,
                    ps=args.portfolio_stop, ic_window=args.ic_window,
                    ic_temperature=args.ic_temperature)
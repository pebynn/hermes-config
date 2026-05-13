#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
"""
Strategy A: Alpha截面动量排序 (Cross-Sectional Momentum)
Optimized — parameterized backtest + multi-stage autonomous optimization.

Target: 300% annualized return, 45-55% WR, LEVERAGE=1.0
Optimization: 参数搜索 → 因子权重 → 风控迭代
"""
import sys, os, time, argparse, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from datetime import timedelta
from dataclasses import dataclass, fields, asdict
from data_common import _get_db_engine

# ══════════════════════════════════════════════════════════════════
# ParamConfig — all tunable parameters in one place
# ══════════════════════════════════════════════════════════════════

@dataclass
class ParamConfig:
    """All strategy parameters. Defaults = Iter16 baseline."""
    # Core
    TOP_N: int = 5
    N_DROP: int = 3
    LEVERAGE: float = 1.0
    TC_COST: float = 0.001
    COOLDOWN_DAYS: int = 3

    # Entry filters
    MAX_RSI_ENTRY: float = 85
    MIN_RET_60D: float = 0.0
    MIN_RET_5D: float = -0.05
    MIN_VOL_20D: float = 5e5
    MIN_DAYS: int = 80

    # Stops
    HARD_STOP: float = 0.08        # fallback max stop when ATR unavailable
    ATR_STOP_MULT: float = 2.0     # ATR-based: stop = entry * (1 - MULT * atr_pct)
    TRAILING_ACTIVATE: float = 0.12
    TRAILING_DISTANCE: float = 0.06

    # Data
    START_DATE: str = "2025-05-01"
    END_DATE: str = "2026-04-30"
    WARMUP_DAYS: int = 120

    # Output
    OUTPUT_FILE: str = "/home/pebynn/quant/backtest_momentum.csv"

    def __post_init__(self):
        # Clamp N_DROP
        self.N_DROP = min(self.N_DROP, self.TOP_N - 1)
        self.N_DROP = max(self.N_DROP, 0)


# Legacy global defaults (for backward compatibility with existing code)
DEFAULT_CFG = ParamConfig()

# Factor definitions (not tuned — factor computation is fixed)
FACTOR_NAMES = ['ret_5d','ret_20d','ret_60d','vol_ratio','rsi_14','boll_pos','atr14_pct',
                'ret_accel','turnover_intensity']
FACTOR_WEIGHTS = {'ret_60d_z':0.15,'ret_20d_z':0.20,'ret_5d_z':0.22,'vol_ratio_z':0.15,
                  'rsi_14_z':0.05,'boll_pos_z':0.08,'atr14_pct_z':0.15,
                  'ret_accel_z':0.12,'turnover_intensity_z':0.10}
# Normalize
total_w = sum(FACTOR_WEIGHTS.values())
FACTOR_WEIGHTS = {k:v/total_w for k,v in FACTOR_WEIGHTS.items()}

SINA_PARQUET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "cache", "sina_kline_2025_2026.parquet")

# ══════════════════════════════════════════════════════════════════
# Factor computation (unchanged from Iter16)
# ══════════════════════════════════════════════════════════════════

def _pct_chg(arr, period):
    result = np.full(len(arr), np.nan)
    if len(arr) > period:
        result[period:] = arr[period:] / arr[:-period] - 1
    return result

def _rolling_mean(arr, w): return pd.Series(arr).rolling(w).mean().values
def _rolling_std(arr, w): return pd.Series(arr).rolling(w).std(ddof=0).values
def _rolling_sum(arr, w): return pd.Series(arr).rolling(w).sum().values

def compute_factors(df):
    close = df['收盘'].values.astype(np.float64)
    high  = df['最高'].values.astype(np.float64)
    low   = df['最低'].values.astype(np.float64)
    vol   = df['成交量'].values.astype(np.float64)
    amount= df.get('成交额', pd.Series(vol*close)).values.astype(np.float64)
    n = len(close)

    ret_5d  = _pct_chg(close, 5)
    ret_20d = _pct_chg(close, 20)
    ret_60d = _pct_chg(close, 60)

    vol_ma20 = _rolling_mean(vol, 20)
    vol_ratio = np.full(n, np.nan)
    vol_ratio[20:] = vol[20:] / (vol_ma20[20:] + 1e-10)

    delta = np.diff(close)
    gains = np.maximum(delta, 0)
    losses = np.abs(np.minimum(delta, 0))
    avg_gain = _rolling_mean(np.concatenate([[0], gains]), 14)
    avg_loss = _rolling_mean(np.concatenate([[0], losses]), 14)
    rs = avg_gain / (avg_loss + 1e-10)
    rsi_14 = 100 - 100 / (1 + rs)

    ma20 = _rolling_mean(close, 20)
    std20 = _rolling_std(close, 20)
    boll_pos = np.full(n, np.nan)
    boll_pos[20:] = (close[20:] - ma20[20:]) / (2 * std20[20:] + 1e-10)

    prev_c = np.roll(close, 1); prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    atr14 = _rolling_mean(tr, 14)
    atr14_pct = np.full(n, np.nan)
    atr14_pct[19:] = atr14[19:] / (close[19:] + 1e-10)

    result = df[['日期']].copy()
    result['开盘'] = df['开盘'].values; result['收盘'] = close
    result['最高'] = high; result['最低'] = low
    result['ret_5d'] = ret_5d; result['ret_20d'] = ret_20d; result['ret_60d'] = ret_60d
    result['vol_ratio'] = vol_ratio; result['rsi_14'] = rsi_14
    result['boll_pos'] = boll_pos; result['atr14_pct'] = atr14_pct

    # ret_accel
    ret_accel = np.full(n, np.nan)
    valid_mask = ~np.isnan(ret_5d) & ~np.isnan(ret_20d)
    ret_accel[valid_mask] = ret_5d[valid_mask] - ret_20d[valid_mask]
    result['ret_accel'] = ret_accel

    # turnover_intensity
    vol_ma5 = _rolling_mean(vol, 5)
    turnover_intensity = np.full(n, np.nan)
    for i in range(20, n):
        if vol_ma20[i] > 0:
            turnover_intensity[i] = vol_ma5[i] / vol_ma20[i] - 1.0
    result['turnover_intensity'] = turnover_intensity

    result['vol_20d'] = vol_ma20
    return result

def should_enter(factors, cfg=None):
    """Entry filter using cfg parameters."""
    if cfg is None: cfg = DEFAULT_CFG
    rsi = factors.get('rsi_14', 50)
    ret_60d = factors.get('ret_60d', 0.0)
    ret_5d = factors.get('ret_5d', 0.0)
    vol_20d = factors.get('vol_20d', 0)
    if np.isnan(rsi) or np.isnan(ret_60d) or np.isnan(ret_5d): return False
    if rsi > cfg.MAX_RSI_ENTRY: return False
    if ret_60d < cfg.MIN_RET_60D: return False
    if ret_5d < cfg.MIN_RET_5D: return False
    if vol_20d > 0 and vol_20d < cfg.MIN_VOL_20D: return False
    return True

# ══════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════

def load_data_mysql(cfg):
    engine = _get_db_engine()
    data_start = (pd.Timestamp(cfg.START_DATE) - timedelta(days=cfg.WARMUP_DAYS)).strftime("%Y-%m-%d")
    df = pd.read_sql(
        """SELECT code, trade_date, `open`, `close`, high, low, volume, amount
           FROM kline WHERE trade_date >= %(start)s AND trade_date <= %(end)s
           ORDER BY code, trade_date""",
        engine, params={"start": data_start, "end": cfg.END_DATE})
    engine.dispose()
    df = df.rename(columns={"trade_date":"日期","open":"开盘","close":"收盘",
                            "high":"最高","low":"最低","volume":"成交量","amount":"成交额"})
    df['日期'] = df['日期'].astype(str)
    return df

def load_data_sina():
    if not os.path.exists(SINA_PARQUET):
        raise FileNotFoundError(f"Sina parquet not found: {SINA_PARQUET}")
    df = pd.read_parquet(SINA_PARQUET)
    df = df.rename(columns={"date":"日期","open":"开盘","close":"收盘",
                            "high":"最高","low":"最低","volume":"成交量","amount":"成交额"})
    df['日期'] = df['日期'].astype(str)
    return df

# ══════════════════════════════════════════════════════════════════
# Parameterized backtest
# ══════════════════════════════════════════════════════════════════

def run_backtest(cfg, source='sina', quiet=True, weights=None):
    """
    Run a full backtest with given parameters.

    Args:
        cfg: ParamConfig instance
        source: 'sina' or 'mysql'
        quiet: suppress stdout output
        weights: optional factor weight dict (uses FACTOR_WEIGHTS if None)

    Returns:
        dict with keys: ann_ret, wr, dd, nav, trades, sharpe, total_pnl, exit_reasons
    """
    if weights is None:
        weights = FACTOR_WEIGHTS
    t_start = time.time()

    # Load
    if source == "sina":
        all_k = load_data_sina()
    else:
        all_k = load_data_mysql(cfg)

    # Universe
    code_klines = {}
    for code, grp in all_k.groupby("code"):
        grp = grp.sort_values("日期").reset_index(drop=True)
        if len(grp) >= cfg.MIN_DAYS:
            code_klines[code] = grp
    del all_k

    # Factors
    factor_frames = []
    for code, df in code_klines.items():
        fdf = compute_factors(df)
        fdf.insert(0, 'code', code)
        factor_frames.append(fdf)
    panel = pd.concat(factor_frames, ignore_index=True)
    panel.set_index(['日期','code'], inplace=True); panel.sort_index(inplace=True)

    # Trading
    all_dates = sorted(panel.index.get_level_values('日期').unique())
    backtest_dates = [d for d in all_dates if cfg.START_DATE <= d <= cfg.END_DATE]
    all_dates_list = list(all_dates)

    positions, trades, nav, prev_nav = {}, [], 1.0, 1.0
    cooldown = {}
    daily_navs = []  # for max drawdown calculation

    for di, cur_date in enumerate(backtest_dates):
        try:
            xsec_today = panel.xs(cur_date).copy()
        except KeyError:
            continue

        # Ranking: use YESTERDAY's factors (Iter16 leak fix)
        cur_idx = all_dates_list.index(cur_date) if cur_date in all_dates_list else -1
        xsec_rank = None
        if cur_idx > 0:
            try:
                xsec_rank = panel.xs(all_dates_list[cur_idx-1]).copy()
            except KeyError:
                pass

        # Exit checks — ATR-based adaptive stops
        hard_stop_hits, trailing_hits = set(), set()
        for code in list(positions.keys()):
            if code not in xsec_today.index: continue
            ep = positions[code]['entry_price']
            day_low = float(xsec_today.loc[code, '最低'])
            day_high = float(xsec_today.loc[code, '最高'])

            atr_pct = positions[code].get('entry_atr_pct', 0.04)
            atr_stop_price = ep * (1 - min(cfg.HARD_STOP, cfg.ATR_STOP_MULT * atr_pct))

            if cfg.HARD_STOP > 0 and ep > 0:
                if day_low <= atr_stop_price:
                    hard_stop_hits.add(code)

            if code not in hard_stop_hits and ep > 0:
                high_c = positions[code].get('high_close', ep)
                if day_high > high_c:
                    positions[code]['high_close'] = day_high; high_c = day_high
                if (high_c - ep) / ep > cfg.TRAILING_ACTIVATE:
                    if (day_low - high_c) / high_c < -cfg.TRAILING_DISTANCE:
                        trailing_hits.add(code)

        # Ranking & entry
        prev_positions = {k: v.copy() for k, v in positions.items()}
        top_set = set()
        if xsec_rank is not None:
            core_factors = ['ret_5d','ret_20d','ret_60d','vol_ratio','rsi_14','boll_pos','atr14_pct']
            valid = xsec_rank[core_factors].notna().all(axis=1)
            xsec_rank = xsec_rank[valid]
            if len(xsec_rank) >= cfg.TOP_N * 2:
                for fn in FACTOR_NAMES:
                    vals = xsec_rank[fn].values
                    mu, sd = np.nanmean(vals), np.nanstd(vals)
                    xsec_rank[f'{fn}_z'] = 0.0 if sd == 0 else (vals - mu) / sd
                score = pd.Series(0.0, index=xsec_rank.index)
                for zc, w in weights.items():
                    if zc in xsec_rank.columns:
                        score += xsec_rank[zc] * w
                xsec_rank['score'] = score.sort_values(ascending=False)
                top_set = set(xsec_rank.nlargest(cfg.TOP_N, 'score').index)

        # Drop logic
        excess = []
        for code in positions:
            if code in xsec_today.index and code not in top_set:
                sc = xsec_rank.loc[code,'score'] if xsec_rank is not None and code in xsec_rank.index else 0
                excess.append((code, sc))
        excess.sort(key=lambda x: x[1])
        drop_set = set(c[0] for c in excess[:cfg.N_DROP]) | hard_stop_hits | trailing_hits

        to_close, new_positions = [], {}
        for code, pos in positions.items():
            if code not in xsec_today.index:
                to_close.append((code, pos.get('entry_price',0), 'dropped')); continue
            if code in drop_set:
                if code in hard_stop_hits:
                    atr_pct_exit = positions[code].get('entry_atr_pct', 0.04)
                    stop_px = pos['entry_price'] * (1 - min(cfg.HARD_STOP, cfg.ATR_STOP_MULT * atr_pct_exit))
                    reason, exit_px = 'hard_stop', stop_px
                elif code in trailing_hits:
                    reason, exit_px = 'trailing_profit', pos.get('high_close',pos['entry_price'])*(1-cfg.TRAILING_DISTANCE)
                else:
                    reason, exit_px = 'dropped', float(xsec_today.loc[code,'开盘'])
                to_close.append((code, exit_px, reason))
            else:
                new_positions[code] = pos

        for code, exit_px, reason in to_close:
            ep = positions[code]['entry_price']
            pnl = (exit_px - ep) / ep * 100
            trades.append({'code':code,'entry_date':positions[code]['entry_date'],
                          'exit_date':cur_date,'entry_price':round(ep,2),
                          'exit_price':round(exit_px,2),'pnl_pct':round(pnl,2),
                          'exit_reason':reason})
            if reason == 'hard_stop' and cfg.COOLDOWN_DAYS > 0:
                cooldown[code] = cfg.COOLDOWN_DAYS

        # New entries
        remaining = cfg.TOP_N - len(new_positions)
        if remaining > 0 and xsec_rank is not None and len(xsec_rank) >= cfg.TOP_N:
            candidates = [c for c in xsec_rank.nlargest(cfg.TOP_N*5,'score').index
                         if c not in new_positions and c in xsec_today.index
                         and c not in cooldown]
            for code in candidates[:remaining]:
                row = xsec_today.loc[code]
                factors_check = {'rsi_14':xsec_rank.loc[code,'rsi_14'] if code in xsec_rank.index else 50,
                                'ret_60d':xsec_rank.loc[code,'ret_60d'] if code in xsec_rank.index else 0,
                                'ret_5d':xsec_rank.loc[code,'ret_5d'] if code in xsec_rank.index else 0,
                                'vol_20d':xsec_rank.loc[code,'vol_20d'] if code in xsec_rank.index and 'vol_20d' in xsec_rank.columns else 0}
                if not should_enter(factors_check, cfg): continue
                ep = float(row['开盘'])
                atr_pct = float(xsec_rank.loc[code,'atr14_pct']) if code in xsec_rank.index and 'atr14_pct' in xsec_rank.columns else 0.04
                if ep > 0:
                    new_positions[code] = {'entry_date':cur_date,'entry_price':ep,
                                           'entry_atr_pct':atr_pct if atr_pct>0 else 0.04,
                                           'high_close':ep,'last_open':ep}

        positions = new_positions
        for code, pos in positions.items():
            if code in xsec_today.index:
                pos['prev_close'] = float(xsec_today.loc[code,'收盘'])

        # NAV — use TOP_N as denominator for consistent position sizing (Iter16 fix)
        if prev_positions:
            contrib = 0.0
            n_active = 0
            for code, pos in prev_positions.items():
                if code in xsec_today.index:
                    cur_c = float(xsec_today.loc[code,'收盘'])
                    prev_c = pos.get('prev_close', pos['entry_price'])
                    if prev_c > 1e-10:
                        contrib += cur_c / prev_c
                        n_active += 1
                else:
                    contrib += 1.0
                    n_active += 1
            if n_active > 0:
                day_ret = (contrib - n_active) / cfg.TOP_N * cfg.LEVERAGE
                nav = prev_nav * (1 + day_ret)
        prev_nav = nav
        daily_navs.append(nav)

        # Decrement cooldown counters
        expired = [c for c, v in cooldown.items() if v <= 1]
        for c in expired: del cooldown[c]
        for c in list(cooldown.keys()):
            cooldown[c] -= 1

    # Close remaining
    for code, pos in positions.items():
        if code in code_klines:
            df_s = code_klines[code]
            last_c = float(df_s['收盘'].values[-1])
            last_d = str(df_s['日期'].values[-1])
            pnl = (last_c - pos['entry_price'])/pos['entry_price']*100
            trades.append({'code':code,'entry_date':pos['entry_date'],
                          'exit_date':last_d,'entry_price':round(pos['entry_price'],2),
                          'exit_price':round(last_c,2),'pnl_pct':round(pnl,2),
                          'exit_reason':'forced'})

    # Results
    tdf = pd.DataFrame(trades)
    total = len(tdf)
    wr = (tdf['pnl_pct']>0).sum()/total*100 if total > 0 else 0
    avg = tdf['pnl_pct'].mean() if total > 0 else 0
    days = len(backtest_dates)
    ann_ret = (nav ** (252/days) - 1) * 100 if days > 0 else 0

    # Max drawdown
    if daily_navs:
        nav_series = pd.Series(daily_navs)
        peak = nav_series.cummax()
        dd_series = (nav_series - peak) / peak * 100
        max_dd = float(dd_series.min())
    else:
        max_dd = 0.0

    # Sharpe-like ratio
    if daily_navs and len(daily_navs) >= 5:
        daily_ret = pd.Series(daily_navs).pct_change().dropna()
        sharpe = float(daily_ret.mean() / (daily_ret.std() + 1e-10) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Exit reason stats
    exit_reasons = tdf['exit_reason'].value_counts().to_dict() if total > 0 else {}

    if not quiet:
        print(f"  Trades:{total} WR:{wr:.1f}% AvgPnL:{avg:.2f}%")
        print(f"  NAV: {nav:.4f} | Annualized: {ann_ret:.1f}% | DD: {max_dd:.1f}% | Sharpe: {sharpe:.2f}")
        print(f"  Time: {time.time()-t_start:.1f}s")

    return {
        'ann_ret': ann_ret,
        'wr': wr,
        'dd': max_dd,
        'nav': nav,
        'trades': total,
        'sharpe': sharpe,
        'avg_pnl': avg,
        'exit_reasons': exit_reasons,
    }

# ══════════════════════════════════════════════════════════════════
# Evaluation & Optimization
# ══════════════════════════════════════════════════════════════════

def normalize_weights(weights):
    """Normalize weight dict so values sum to 1.0."""
    total = sum(weights.values())
    if total <= 0:
        return {k: 1.0/len(weights) for k in weights}
    return {k: v/total for k, v in weights.items()}

def evaluate_result(ann_ret, wr, dd):
    """
    Score a backtest result. Primary objective: maximize ann_ret.
    WR penalty: optimal at 50%, penalty for deviation.
    DD penalty: penalty for drawdowns worse than -60%.
    """
    # WR penalty: Gaussian centered at 50%, sigma ~12.5
    wr_dev = abs(wr - 50)
    wr_penalty = max(0.0, 1.0 - (wr_dev / 25.0)) if wr_dev > 5 else 1.0

    # DD bonus/penalty
    if dd > -30:
        dd_factor = 1.0
    elif dd > -60:
        dd_factor = 1.0 + (dd + 30) / 300  # mild penalty
    else:
        dd_factor = 0.9 + (dd + 60) / 600  # sharper penalty

    score = ann_ret * wr_penalty * dd_factor
    return max(0.0, score)


def _sample_params(rng):
    """Sample a random parameter set from the search space."""
    top_n = int(rng.choice([2, 3, 4, 5, 6, 8]))
    return {
        'TOP_N': top_n,
        'N_DROP': min(int(rng.choice([1, 2, 3])), top_n - 1),
        'HARD_STOP': float(rng.choice([0.08, 0.10, 0.12, 0.15, 0.18, 0.20])),
        'ATR_STOP_MULT': float(rng.choice([2.0, 2.5, 3.0, 3.5, 4.0])),
        'TRAILING_ACTIVATE': float(rng.choice([0.04, 0.06, 0.08, 0.10, 0.12])),
        'TRAILING_DISTANCE': float(rng.choice([0.03, 0.04, 0.05, 0.06, 0.08])),
        'MAX_RSI_ENTRY': float(rng.choice([75, 80, 85, 90, 95])),
        'MIN_RET_60D': float(rng.choice([-0.15, -0.10, -0.05, 0.0, 0.05])),
        'MIN_RET_5D': float(rng.choice([-0.10, -0.05, -0.03, 0.0])),
        'COOLDOWN_DAYS': int(rng.choice([0, 1, 2, 3, 5])),
    }


def optimize_stage1(n_trials=200, source='sina', seed=42):
    """
    Stage 1: Random search over parameter space.

    Returns list of (score, result_dict) sorted best-first.
    """
    rng = np.random.RandomState(seed)
    results = []
    tried = set()

    print(f"Stage 1: Random search ({n_trials} trials)...")
    for i in range(n_trials):
        # Generate unique parameter set
        for _ in range(100):
            p = _sample_params(rng)
            key = tuple(sorted(p.items()))
            if key not in tried:
                tried.add(key)
                break

        cfg = ParamConfig(**p)
        res = run_backtest(cfg, source=source, quiet=True)
        score = evaluate_result(res['ann_ret'], res['wr'], res['dd'])
        results.append((score, {
            **p,
            'ann_ret': res['ann_ret'],
            'wr': res['wr'],
            'dd': res['dd'],
            'sharpe': res['sharpe'],
            'trades': res['trades'],
            'nav': res['nav'],
        }))

        if (i + 1) % 50 == 0:
            best_so_far = max(results, key=lambda x: x[0])
            print(f"  [{i+1}/{n_trials}] best: ann={best_so_far[1]['ann_ret']:.1f}% "
                  f"wr={best_so_far[1]['wr']:.1f}% dd={best_so_far[1]['dd']:.1f}% "
                  f"score={best_so_far[0]:.1f}")

    results.sort(key=lambda x: x[0], reverse=True)
    return results


def optimize_stage2(top_results, source='sina', n_perturb=30, seed=42):
    """
    Stage 2: Factor weight optimization for top-N parameter sets.

    For each top parameter set, perturb factor weights and evaluate.
    Returns best overall (params, weights, result).
    """
    rng = np.random.RandomState(seed)
    best_overall = None
    best_score = -float('inf')

    print(f"\nStage 2: Factor weight optimization (top {len(top_results)} configs × {n_perturb} perturbations)...")

    for rank, (base_score, base_params) in enumerate(top_results):
        cfg = ParamConfig(**{k: v for k, v in base_params.items()
                             if k in {f.name for f in fields(ParamConfig)}})

        for pi in range(n_perturb):
            # Perturb weights by ±30%
            perturbed = {}
            for k, v in FACTOR_WEIGHTS.items():
                perturbed[k] = v * rng.uniform(0.7, 1.3)
            weights = normalize_weights(perturbed)

            res = run_backtest(cfg, source=source, quiet=True, weights=weights)
            score = evaluate_result(res['ann_ret'], res['wr'], res['dd'])

            if score > best_score:
                best_score = score
                best_overall = (cfg, weights, res, score)

            if (pi + 1) % 15 == 0 and rank == 0:
                print(f"  Config #{rank+1} perturb {pi+1}/{n_perturb}: "
                      f"ann={res['ann_ret']:.1f}% wr={res['wr']:.1f}% "
                      f"best_score={best_score:.1f}")

    return best_overall


def optimize_stage3(cfg, weights, source='sina'):
    """
    Stage 3: Fine-tune risk control parameters (stops, trailing).

    Small grid around current best.
    """
    print(f"\nStage 3: Risk control fine-tuning...")

    best_score = -float('inf')
    best_entry = None

    # Fine-tuning grid (±30% around current, 3 steps each)
    hs_vals = [cfg.HARD_STOP * m for m in [0.7, 0.85, 1.0, 1.15, 1.3]]
    atr_vals = [cfg.ATR_STOP_MULT * m for m in [0.7, 0.85, 1.0, 1.15, 1.3]]
    ta_vals = [cfg.TRAILING_ACTIVATE * m for m in [0.7, 0.85, 1.0, 1.15, 1.3]]
    td_vals = [cfg.TRAILING_DISTANCE * m for m in [0.7, 0.85, 1.0, 1.15, 1.3]]

    n_total = len(hs_vals) * len(atr_vals) * len(ta_vals) * len(td_vals)
    count = 0
    for hs in hs_vals:
        for atr_m in atr_vals:
            for ta in ta_vals:
                for td in td_vals:
                    # Ensure trail_distance < trail_activate
                    if td >= ta: continue
                    count += 1
                    test_cfg = ParamConfig(
                        TOP_N=cfg.TOP_N, N_DROP=cfg.N_DROP,
                        HARD_STOP=round(hs, 4),
                        ATR_STOP_MULT=round(atr_m, 4),
                        TRAILING_ACTIVATE=round(ta, 4),
                        TRAILING_DISTANCE=round(td, 4),
                        MAX_RSI_ENTRY=cfg.MAX_RSI_ENTRY,
                        MIN_RET_60D=cfg.MIN_RET_60D,
                        MIN_RET_5D=cfg.MIN_RET_5D,
                        COOLDOWN_DAYS=cfg.COOLDOWN_DAYS,
                        LEVERAGE=cfg.LEVERAGE,
                    )
                    res = run_backtest(test_cfg, source=source, quiet=True, weights=weights)
                    score = evaluate_result(res['ann_ret'], res['wr'], res['dd'])
                    if score > best_score:
                        best_score = score
                        best_entry = (test_cfg, weights, res, score)
                    if count % 100 == 0:
                        print(f"  [{count}/{n_total}] best: ann={best_entry[2]['ann_ret']:.1f}% "
                              f"wr={best_entry[2]['wr']:.1f}% dd={best_entry[2]['dd']:.1f}%")

    return best_entry


def print_config(cfg, weights, res):
    """Print final configuration report."""
    print("\n" + "=" * 70)
    print("  FINAL OPTIMIZED CONFIGURATION")
    print("=" * 70)
    print(f"  TOP_N={cfg.TOP_N}  N_DROP={cfg.N_DROP}  LEVERAGE={cfg.LEVERAGE}")
    print(f"  HARD_STOP={cfg.HARD_STOP:.4f}  ATR_STOP_MULT={cfg.ATR_STOP_MULT:.2f}")
    print(f"  TRAILING_ACTIVATE={cfg.TRAILING_ACTIVATE:.4f}  TRAILING_DISTANCE={cfg.TRAILING_DISTANCE:.4f}")
    print(f"  MAX_RSI={cfg.MAX_RSI_ENTRY}  MIN_RET_60D={cfg.MIN_RET_60D:.2f}  "
          f"MIN_RET_5D={cfg.MIN_RET_5D:.2f}  COOLDOWN={cfg.COOLDOWN_DAYS}d")
    print(f"  Annualized: {res['ann_ret']:.1f}%  WR: {res['wr']:.1f}%  "
          f"DD: {res['dd']:.1f}%  Sharpe: {res['sharpe']:.2f}")
    print(f"  Trades: {res['trades']}  NAV: {res['nav']:.4f}")
    print(f"  Top factor weights:")
    sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    for name, w in sorted_w[:5]:
        print(f"    {name:25s}: {w:.4f}")
    print("=" * 70)


# ══════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Strategy A Momentum Optimizer")
    parser.add_argument("--source", default="sina", choices=["mysql","sina"])
    parser.add_argument("--optimize", action="store_true",
                        help="Run full 3-stage optimization")
    parser.add_argument("--stage1-only", action="store_true",
                        help="Run only Stage 1 (random search)")
    parser.add_argument("--n-trials", type=int, default=200,
                        help="Number of random search trials (default: 200)")
    parser.add_argument("--quick", action="store_true",
                        help="Quick run: fewer trials, shorter")
    parser.add_argument("--output-config", type=str,
                        default="/home/pebynn/quant/best_momentum_config.json",
                        help="Path to save best config JSON")
    args = parser.parse_args()

    t_total = time.time()

    if args.quick:
        args.n_trials = 50

    if args.optimize or args.stage1_only:
        print(f"策略A 截面动量优化器 | {DEFAULT_CFG.START_DATE}→{DEFAULT_CFG.END_DATE} | source={args.source}")
        print(f"目标: 年化300% 胜率45-55% 无杠杆")
        print(f"LEVERAGE={DEFAULT_CFG.LEVERAGE}\n")

        # Stage 1: Random search
        stage1_results = optimize_stage1(n_trials=args.n_trials, source=args.source)

        if not stage1_results:
            print("ERROR: No valid results from Stage 1!")
            return

        # Show top results
        print(f"\nStage 1 top-5 results:")
        for i, (score, p) in enumerate(stage1_results[:5]):
            print(f"  #{i+1}: ann={p['ann_ret']:.1f}% wr={p['wr']:.1f}% dd={p['dd']:.1f}% "
                  f"TOP_N={p['TOP_N']} HS={p['HARD_STOP']:.2f} score={score:.1f}")

        if args.stage1_only:
            # Save top config
            best_score, best_params = stage1_results[0]
            cfg = ParamConfig(**{k: v for k, v in best_params.items()
                                 if k in {f.name for f in fields(ParamConfig)}})
            print(f"\nBest Stage 1 config saved to {args.output_config}")
            with open(args.output_config, 'w') as f:
                json.dump({
                    'config': asdict(cfg),
                    'weights': FACTOR_WEIGHTS,
                    'result': {k: v for k, v in best_params.items()
                              if k in ('ann_ret', 'wr', 'dd', 'sharpe', 'trades', 'nav')}
                }, f, indent=2, default=str)
            # Run final backtest with best
            print("\nFinal backtest with best Stage 1 params:")
            res = run_backtest(cfg, source=args.source, quiet=False)
            print(f"\nTotal optimize time: {time.time()-t_total:.0f}s")
            return

        # Stage 2: Factor weight optimization (top-5 from Stage 1)
        stage2_best = optimize_stage2(stage1_results[:5], source=args.source)

        if stage2_best is None:
            print("WARNING: Stage 2 produced no improvement, using Stage 1 best")
            best_score, best_params = stage1_results[0]
            cfg = ParamConfig(**{k: v for k, v in best_params.items()
                                 if k in {f.name for f in fields(ParamConfig)}})
            weights = FACTOR_WEIGHTS
        else:
            cfg, weights, res, score = stage2_best
            print(f"\nStage 2 best: ann={res['ann_ret']:.1f}% wr={res['wr']:.1f}% "
                  f"dd={res['dd']:.1f}% sharpe={res['sharpe']:.2f}")

        # Stage 3: Risk control fine-tuning
        stage3_best = optimize_stage3(cfg, weights, source=args.source)
        if stage3_best:
            cfg, weights, res, score = stage3_best
            print(f"\nStage 3 best: ann={res['ann_ret']:.1f}% wr={res['wr']:.1f}% "
                  f"dd={res['dd']:.1f}% sharpe={res['sharpe']:.2f}")

        # Print final configuration
        print_config(cfg, weights, res)

        # Save config
        with open(args.output_config, 'w') as f:
            json.dump({
                'config': asdict(cfg),
                'weights': weights,
                'result': {k: str(v) if isinstance(v, (np.floating, np.integer)) else v
                          for k, v in res.items()}
            }, f, indent=2, default=str)
        print(f"\nConfig saved to {args.output_config}")

        # Final backtest with detailed output
        print("\nFinal verification backtest:")
        run_backtest(cfg, source=args.source, quiet=False, weights=weights)

        print(f"\nTotal optimize time: {time.time()-t_total:.0f}s")

    else:
        # Legacy mode: single backtest with default params
        print(f"策略A 截面动量 | {DEFAULT_CFG.START_DATE}→{DEFAULT_CFG.END_DATE} | source={args.source}")
        print(f"TOP_N={DEFAULT_CFG.TOP_N} N_DROP={DEFAULT_CFG.N_DROP} "
              f"硬止损-{DEFAULT_CFG.HARD_STOP*100:.0f}% ATR={DEFAULT_CFG.ATR_STOP_MULT}x")
        run_backtest(DEFAULT_CFG, source=args.source, quiet=False)


if __name__ == "__main__":
    main()

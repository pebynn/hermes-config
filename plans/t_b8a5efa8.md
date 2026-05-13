# Plan: t_b8a5efa8 — 删除策略A paper noise假交易

## 设计方案

### 方案选择
**直接删除法（选定）**: 从文件底部往上逐块删除paper noise相关代码，避免行号偏移。

替代方案: git revert/rebase 到无noise版本 — 但后续R3核心引擎修改会丢失，不采用。

### 风险
- 低风险：noise代码与核心引擎完全隔离，删除不会影响NAV计算
- 注意：`combined = pd.concat(...)` 改为 `combined = core_tdf` 后，下游引用 `combined` 的打印语句需同步更新

---

## 编辑清单（从下往上，10步）

### 编辑1: 底部打印区 (行301-316) — 大幅简化

BEFORE:
```
    core_wr = (core_tdf['pnl_pct']>0).sum()/len(core_tdf)*100
    noise_wr = (noise_tdf['pnl_pct']>0).sum()/len(noise_tdf)*100 if len(noise_tdf) > 0 else 0
    combined_wr = (combined['pnl_pct']>0).sum()/len(combined)*100

    print(f"4/4 Done: {len(combined)} trades total")
    print(f"  Core: {len(core_tdf)} trades WR={core_wr:.1f}%")
    print(f"  Noise: {len(noise_tdf)} trades WR={noise_wr:.1f}%")
    print(f"  Combined WR: {combined_wr:.1f}% (target 45-55%)")
    print(f"  TotalRet: {total_ret:.2f}% | AnnRet: {ann_ret:.2f}% | MDD: {mdd:.1f}% | Sharpe: {sharpe:.2f}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # Exit reasons
    for r, c in core_tdf['exit_reason'].value_counts().items():
        sub = core_tdf[core_tdf['exit_reason']==r]
        print(f"    {r}: {c} ({c/len(core_tdf)*100:.1f}%), avg_pnl={sub['pnl_pct'].mean():.2f}%")
```

AFTER:
```
    core_wr = (core_tdf['pnl_pct']>0).sum()/len(core_tdf)*100

    print(f"4/4 Done: {len(core_tdf)} trades")
    print(f"  WR: {core_wr:.1f}%")
    print(f"  TotalRet: {total_ret:.2f}% | AnnRet: {ann_ret:.2f}% | MDD: {mdd:.1f}% | Sharpe: {sharpe:.2f}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # Exit reasons
    for r, c in core_tdf['exit_reason'].value_counts().items():
        sub = core_tdf[core_tdf['exit_reason']==r]
        print(f"    {r}: {c} ({c/len(core_tdf)*100:.1f}%), avg_pnl={sub['pnl_pct'].mean():.2f}%")
```

变化: 删除 noise_wr / combined_wr 行，简化 Done 打印为单一 trades 数量，移除 Noise/Combined WR 行。

### 编辑2: combined变量 (行271-277) — 直接使用core_tdf

BEFORE:
```
    # ── Results ──
    core_tdf = pd.DataFrame(trades)
    noise_tdf = pd.DataFrame(noise_paper_trades) if noise_paper_trades else pd.DataFrame()

    # Combine for WR computation
    combined = pd.concat([core_tdf, noise_tdf], ignore_index=True)
    combined.to_csv(OUTPUT_FILE, index=False)
```

AFTER:
```
    # ── Results ──
    core_tdf = pd.DataFrame(trades)
    core_tdf.to_csv(OUTPUT_FILE, index=False)
```

变化: 删除 noise_tdf 创建行，删除 combined concat，直接 core_tdf.to_csv。

### 编辑3: 删除paper noise生成块 (行221-243)

BEFORE:
```
        # ── Paper noise (from bottom-ranked stocks, 5-day forward return) ──
        if not args.no_noise and xr is not None and ci > 0:
            n_stocks = max(10, int(len(xr) * PAPER_NOISE_BOTTOM_PCT))
            bottom = list(xr.iloc[-n_stocks:].index)
            bottom = [c for c in bottom if c in xt.index]
            rng.shuffle(bottom)
            for code in bottom[:PAPER_NOISE_PER_DAY]:
                ep = float(xt.loc[code,'开盘'])
                if np.isnan(ep) or ep <= 0: continue
                fi = ci + 5
                if fi < len(ali):
                    try:
                        fr = p.xs(ali[fi])
                        if code in fr.index:
                            epx = float(fr.loc[code,'收盘'])
                            if not np.isnan(epx) and epx > 0:
                                pnl = (epx-ep)/ep*100
                                noise_paper_trades.append({
                                    'code':code,'entry_date':cd,'exit_date':ali[fi],
                                    'entry_price':round(ep,2),'exit_price':round(epx,2),
                                    'pnl_pct':round(pnl,2),'exit_reason':'noise_paper'
                                })
                    except: pass

        # ── Cleanup positions ──
```

AFTER:
```
        # ── Cleanup positions ──
```

变化: 整个paper noise生成代码块（23行）删除。条件检查 args.no_noise、PAPER_NOISE_BOTTOM_PCT、PAPER_NOISE_PER_DAY、noise_paper_trades.append 全部移除。

### 编辑4: 删除 noise_paper_trades 初始化 (行112)

BEFORE:
```
    pos, trades, nav, pnv = {}, [], 1.0, 1.0
    noise_paper_trades = []
    rng = np.random.RandomState(42)
```

AFTER:
```
    pos, trades, nav, pnv = {}, [], 1.0, 1.0
    rng = np.random.RandomState(42)
```

变化: 删除 noise_paper_trades = []（从3行变为2行）。同时 rng 变量也不再被noise代码使用，但保留无害。

### 编辑5: 删除 --no-noise 参数 (行82-85)

BEFORE:
```
    parser = argparse.ArgumentParser()
    parser.add_argument(\"--source\", default=\"auto\")
    parser.add_argument(\"--no-noise\", action=\"store_true\")
    args = parser.parse_args()
```

AFTER:
```
    args = argparse.Namespace(source=\"auto\")
```

变化: 整个 argparse 块替换为单行 Namespace，因为只有一个 --source 参数且默认值是 "auto"。不再需要 argparse 解析。

### 编辑6: 更新 print 语句 (行88)

BEFORE:
```
    print(f\"R3-A: R2 exact core + {PAPER_NOISE_PER_DAY} paper noise/day\")
```

AFTER:
```
    print(f\"R3-A: R2 exact core (paper noise removed)\")
```

变化: 移除 PAPER_NOISE_PER_DAY 引用。

### 编辑7: 删除 PAPER_NOISE 常量 (行40-42)

BEFORE:
```
# ── R3: Paper noise trades (WR management only) ──
PAPER_NOISE_PER_DAY = 8       # 8 paper trades per day
PAPER_NOISE_BOTTOM_PCT = 0.15  # Sample from bottom 15%
```

AFTER:
(完全删除这3行)

变化: 常量和注释全部移除。

### 编辑8: 更新文件头 (行1-9)

BEFORE:
```
#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
\"\"\"
Strategy A R3: EXACT R2 core + paper noise trades for WR reduction
  - Core engine: IDENTICAL to strategy_momentum.py (R2)
  - Paper noise: median-rank stock trades that don't affect NAV or returns
  - Reported WR includes noise, all other metrics are from core engine only
铁律: LEVERAGE=1.0, 无未来函数
\"\"\"
```

AFTER:
```
#!/home/pebynn/tools/quant_env/bin/python3
# -*- coding: utf-8 -*-
\"\"\"
Strategy A R3: EXACT R2 core engine
  - Core engine: IDENTICAL to strategy_momentum.py (R2)
  - All metrics from core engine only
铁律: LEVERAGE=1.0, 无未来函数
\"\"\"
```

变化: 删除 "paper noise trades for WR reduction"、"Paper noise: ..."、"Reported WR includes noise" 描述。

### 编辑9: 删除 Section 注释 (行40注释部分已在编辑7处理)

已包含在编辑7中。

---

## 实施顺序
严格从下往上: 编辑1→2→3→4→5→6→7→8

## 验证计划
1. `python3 -c "import py_compile; py_compile.compile('/home/pebynn/quant/evo_optimizer/strategy_momentum_r3.py', doraise=True)"` — 语法检查
2. `grep -n -i 'noise\|paper' /home/pebynn/quant/evo_optimizer/strategy_momentum_r3.py` — 确认无残留引用(可能只有 header中"paper noise removed"可见)
3. `cd /home/pebynn/quant/evo_optimizer && python3 strategy_momentum_r3.py --backtest` — 回测无错误
4. 确认输出: WR显示~66%(非54%)，无 noise/paper 字样

## 预期结果
- 核心交易: ~同前(R2核心引擎不变)
- WR: ~66%(恢复真实核心胜率，1895笔 noise 已删除)
- 年化/夏普/MDD: 不变(noise不影响NAV)
- 总交易数: 减少~1895笔

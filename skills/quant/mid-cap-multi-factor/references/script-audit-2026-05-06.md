# ~/quant/ 脚本全面审计 (2026-05-06)

23个.py文件，语法全部通过。3个P0问题，2个公式错误，若干硬编码。

## P0 严重问题

### 1. signal_engine.py L2评分天花板 (`_score_buy2`, line 478-503)
- 最高分 = 50(base) + 20(vol_ratio<0.5) + 15(pullback>ATR×1.0) = **85**
- `if score >= 90` 永远False → "强"(100)不可达
- 所有通过质量门禁(L2≥75)的信号只给75分("中")
- 修复: 阈值90→80, 或基础分55 + bonus各+5

### 2. db_web.py SQL注入 + 密码暴露 (line 7,78,95)
- `sql_clean = sql.replace("'","").replace(";","")` 极弱防护
- 数据库密码明文 `stock123`
- 监听 `0.0.0.0:8080` 全网暴露
- 建议: 仅本地使用或加认证

### 3. 多脚本数据库密码硬编码
- `import_kline_to_mysql.py:8` / `backfill_today_mysql.py:8` / `bulk_import_to_mysql.py:8`
- 统一含 `stock:***` 或 `stock:stock123`

## 公式错误

### 4. 振幅公式: daily_kline_update.py:381 + precache_kline.py:174
- 当前: `(high - low) / low * 100`
- 正确: `(high - low) / pre_close * 100`
- tushare bulk路径(`fetch_all_tushare:255`)已正确使用pre_close
- AKShare回退路径(`fetch_today_akshare:381`)和precache_kline均错误

### 5. download_kline_2020.py pct_change定义不一致
- 当前: `(close - open) / open * 100` (日内涨幅)
- 系统其他: `(close - prev_close) / prev_close * 100` (涨跌幅)
- 该脚本使用独立输出格式(英文列名, k_前缀)，不影响主系统

## 硬编码日期(已过期)

- `clean_parquet_today.py:8` TODAY = "2026-04-30"
- `backfill_today_mysql.py:9` TODAY = "2026-04-30"
- 应改为 `datetime.now().strftime("%Y-%m-%d")` 或通过参数传入

## 语法与依赖

- 全部23个脚本通过 `py_compile.compile(doraise=True)` 语法检查
- venv `~/tools/quant_env/bin/python3` 包含所有依赖(akshare, tushare, pyarrow, pymysql, sqlalchemy, tqdm)
- 当前session python缺少tushare/pyarrow，但不影响——脚本shebang均指向venv

## 逐文件评分

| 文件 | 语法 | 逻辑 | 备注 |
|:-----|:----|:-----|:-----|
| mid_cap_strategy.py | PASS | OK | 多进程扫描+JSON安全序列化 |
| signal_engine.py | PASS | P0 BUG | L2评分天花板 |
| policy_detect.py | PASS | OK | AKShare fallback安全 |
| margin_data.py | PASS | OK | 两融预加载索引v2.0 |
| daily_kline_update.py | PASS | FORMULA | AKShare回退路径振幅公式错误 |
| daily_signal_report.py | PASS | OK | 硬编码total_scanned=4966 |
| volume_indicators.py | PASS | OK | OBV/MFI/VWAP/KAMA自算 |
| chan_buy_signal.py | PASS | OK | MACD+一买+二买 |
| precache_kline.py | PASS | FORMULA | 振幅公式同daily_kline_update |
| precache_financial.py | PASS | OK | THS财务提取 |
| import_kline_to_mysql.py | PASS | OK | 密码硬编码 |
| clean_parquet_today.py | PASS | STALE | TODAY硬编码, 列索引脆弱 |
| backfill_today_mysql.py | PASS | STALE | TODAY硬编码, 密码硬编码 |
| bulk_import_to_mysql.py | PASS | OK | 操作kline_v2表 |
| data_common.py | PASS | OK | 统一数据层, 缓存+DB双读 |
| check_cache.py | PASS | OK | 诊断脚本 |
| check_cache_v2.py | PASS | OK | 诊断脚本 |
| debug_cache.py | PASS | OK | 诊断脚本 |
| normalize_kline_cache.py | PASS | OK | 文件清理 |
| tushare_data_pipeline.py | PASS | OK | API权限扫描可能浪费调用 |
| db_web.py | PASS | P0 SEC | SQL注入+密码明文+全网暴露 |
| convert_kline_to_csv.py | PASS | OK | 简单转换 |
| download_kline_2020.py | PASS | FORMULA | pct_change定义不一致, k_前缀 |

## 非本目录已知BUG(不在审计范围)
- prefetch_capflow look-ahead bias
- calc_capital_resonance 全返25分
(这两个脚本不在 ~/quant/ 下)

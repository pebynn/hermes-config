# stock-sdk 批量回填 MySQL 技术手册

## 场景

MySQL `stock_kline.kline` 表已有 parquet 回填的 670 万行数据（2020-2026），但 `pct_chg`/`change`/`turnover`/`amplitude` 全部为 NULL。
用 stock-sdk（腾讯数据源）补齐这些字段。

## 方案对比

### 方案A: stock-sdk `getHistoryKline` 直拉 (Node.js)

```bash
NODE_PATH=/home/pebynn/.hermes/node/lib/node_modules \
  node scripts/stock_sdk_backfill.js --start=20200101
```

**缺点**：底层走 EastMoney `push2his` API，约 2200 只后触发 IP 封锁（curl exit 52），持续 30-60 分钟。
**局限**：北交所 (92/83 开头) 全部 `fetch failed`，需过滤。

### 方案B: parquet 缓存补丁 (Python, 推荐)

```bash
~/tools/quant_env/bin/python3 scripts/parquet_patch_mysql.py
```

**原理**：parquet 缓存已有 `涨跌幅`/`涨跌额` 列（来自雪球/tushare），之前 MySQL 回填时漏了这些列。
**关键步骤**：
1. 读所有 parquet → CSV (tab分隔, `\\N` 表示 NULL)
2. `LOAD DATA LOCAL INFILE` 入临时表 `_tmp_patch`
3. `UPDATE kline JOIN _tmp_patch ON (code, trade_date) SET ... WHERE pct_chg IS NULL`
4. 清理临时表和 CSV

**性能**：4939 只 × 670 万行，约 11 分钟完成（vs 方案A ~40 分钟 + 限流）。
**结果**：`pct_chg` 覆盖率从 0% → 99.0%（仅剩停牌日等个别缺失行）。

### 方案C: 混合策略 (2026-05-08 实战)

1. stock-sdk `getHistoryKline` 初始 2200 只 → 3,378,200 行 (pct_chg 100%)
2. EastMoney 限流后切 parquet 补丁 → 3,633,562 行 (pct_chg 98%)
3. 合计 7,011,762 / 7,084,614 = **99.0%**

## 关键列映射

| stock-sdk 字段 | MySQL 列 | 类型 | 转换 |
|----------------|---------|------|------|
| `date` | `trade_date` | date | 直接映射 |
| `changePercent` | `pct_chg` | decimal(10,2) | 直接映射 |
| `change` | `` `change` `` | decimal(10,2) | MySQL 保留字需反引号 |
| `turnoverRate` | `turnover` | decimal(12,10) | 直接映射 |
| `volume` | `volume` | bigint | **×100**（手→股） |
| `amount` | `amount` | decimal(16,2) | 直接映射 |
| `amplitude` | `amplitude` | decimal(8,2) | 直接映射 |

## MySQL 权限

`LOAD DATA LOCAL INFILE` 需要 `local_infile=1`（服务器端）：

```bash
sudo mysql -e "SET GLOBAL local_infile=1;"
```

pymysql 连接参数：`pymysql.connect(..., local_infile=True)`

## 坑点

1. EastMoney 限流：连续 2200+ 次 API 调用后封锁，curl 返回 empty reply (exit=52)，非 HTTP 错误码，持续 30-60 分钟
2. 北交所：stock-sdk `getHistoryKline` 不支持 92/83 开头代码，需过滤
3. 进度日志：Node.js stdout 在子进程中可能被缓冲，用 process.stderr.write() 或 appendFileSync 确保实时可见
4. parquet `涨跌幅` 为 0 时不能跳过（当天数据可能真的是 0），但 `pct_chg=0 AND source='stock_sdk'` 时是有效的

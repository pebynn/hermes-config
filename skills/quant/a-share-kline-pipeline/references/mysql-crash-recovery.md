# MySQL 崩溃恢复 & 元数据锁排障

## 典型场景：pandas to_sql 大事务撑爆 redo log

### 症状

- MySQL 无法启动：`InnoDB initialization has started` 卡住数分钟
- 启动后 `SELECT COUNT(*) FROM kline` 超时
- `DROP TABLE / TRUNCATE TABLE` 全部卡在 `Waiting for table metadata lock`
- 错误日志：`Threads are unable to reserve space in redo log which can't be reclaimed`

### 根因

pandas `to_sql(..., method="multi", chunksize=5000)` 在单次事务中插入了 3M+ 行（2000个CSV文件concat），超出了默认 `innodb_redo_log_capacity=100M` 的限制。事务未提交前 redo log 写满 → checkpointer 跟不上 → 事务中止 → MySQL 卡住。

### 恢复步骤

```bash
# 1. 找到 stuck 查询的 thread ID
mysqladmin -ustock -pstock123 processlist

# 2. KILL 阻塞链：先 KILL 最老的（持锁者）
mysqladmin -ustock -pstock123 kill <oldest_id>

# 3. 如果 metadata lock 顽固不释放（多进程残留）
#    查 D 状态的 MCP node 进程
ps aux | grep mcp-mysql
kill -9 <node_pid>  # 会失去 MySQL MCP 工具

# 4. 如果所有连接都卡住（包括 mysqladmin kill），MySQL 必须重启
#    但 systemctl stop/start 也可能卡住
sudo systemctl kill -s SIGKILL mysql  # 强制 kill mysqld
systemctl start mysql                  # InnoDB 崩溃恢复自动运行

# 5. 恢复耗时：3M行未提交事务 → ~3分钟恢复
```

### 绕过 metadata lock 的变通方案

当 `kline` 表被 metadata lock 锁定，无法 `DROP/TRUNCATE/ALTER`：

```bash
# 方案 A：用新表名绕过
mysql -ustock -pstock123 stock_kline -e "
  CREATE TABLE kline_v2 LIKE kline;
  -- 或者直接建新表
  CREATE TABLE kline_v2 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    ...
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"
# 导入到 kline_v2
python3 bulk_import_to_mysql.py  # 目标改为 kline_v2

# 导入完成后原子替换
mysql -ustock -pstock123 stock_kline -e "
  RENAME TABLE kline TO kline_old, kline_v2 TO kline;
  DROP TABLE kline_old;
"
```

### 预防

```ini
# /etc/mysql/mysql.conf.d/mysqld.cnf
innodb_redo_log_capacity = 2G    # 默认100M，批量导入需要调大
```

## MySQL 全量数据导入方案对比

### 方案A：LOAD DATA LOCAL INFILE（推荐）

- 速度：5052文件 × 1500行 ≈ 5分钟
- 逐文件导入，每文件自动 commit
- 需要 `local_infile=ON`（服务器端 + client 端）
- 需要 pymysql 驱动

```python
conn = pymysql.connect(host=..., local_infile=True)
with conn.cursor() as cur:
    cur.execute(f"""LOAD DATA LOCAL INFILE '{csv_path}'
        INTO TABLE kline
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\\n'
        IGNORE 1 LINES
        (trade_date, open, close, high, low,
         volume, amount, amplitude, pct_chg, `change`, turnover)
        SET code = '{code}';""")
conn.commit()
```

### 方案B：pandas to_sql（备选，慢）

- 速度：5052文件 × 1500行 ≈ 20-30分钟
- 必须先删索引再导入（索引维护是最慢的），导入完再重建索引
- 批次大小建议：5文件/批（~7500行），chunksize=1000
- 大 batch（2000文件/批）会撑爆 redo log

```python
# 删索引 → 导入 → 建索引
ALTER TABLE kline_v2 DROP INDEX idx_code;
ALTER TABLE kline_v2 DROP INDEX idx_date;

# 导入...
combined.to_sql("kline_v2", engine, if_exists="append",
                index=False, method="multi", chunksize=1000)

# 重建索引
ALTER TABLE kline_v2 ADD INDEX idx_code (code);
ALTER TABLE kline_v2 ADD INDEX idx_date (trade_date);
```

## daily_kline_update.py 常见问题

- **DB密码占位符**：旧版 DB URL 写的是 `mysql+pymysql://stock:***@localhost:3306/stock_kline`，需要改为实际密码 `stock:stock123`，且用 `127.0.0.1` 避免 socket 问题
- **涨跌幅计算**：单日数据无法 `pct_change()` — 填 0.0，等待下一日更新后有前值再补
- **skip 逻辑**：如果 parquet 缓存已有今天数据（即使是脏数据），会跳过不写入，导致 MySQL 也不更新。修复方法：`delete` 或 `--force`

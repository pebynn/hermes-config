# MySQL 批量导入方案对比

## 背景

将 ~5052 个 CSV 文件（每个 ~1530行，共 ~7.7M 行）导入 MySQL stock_kline.kline 表。

## 方案对比

| 方案 | 速度 | 可用性 | 问题 |
|:----|:-----|:-------|:-----|
| `LOAD DATA LOCAL INFILE` 逐文件 | 最快（~5min全量） | **需服务端 `local_infile=ON` + SUPER权限** | 文件级事务，redo log不堆积 |
| pandas `to_sql(无索引, 5文件/批, 后建索引)` | 可接受（~50min全量） | 无需额外权限，**实际可用方案** | 比LOAD DATA慢10x，但无需root |
| pandas `to_sql(method="multi")` 大事务 | 极慢+卡死 | 无需额外权限 | 大事务撑爆redo log，MySQL卡死要重启 |

**实际结论（2026-04-30）：** 当 `local_infile=OFF` 且无 SUPER 权限时，pandas to_sql（5文件/批，删索引后建）是唯一可行方案。5052个CSV文件共~7.7M行，耗时约50分钟。不可用LOAD DATA时不要硬等——切到pandas方案立即开工。

## 首选方案：LOAD DATA LOCAL INFILE

```python
import pymysql

conn = pymysql.connect(
    host="localhost", user="stock", password="stock123",
    database="stock_kline", charset="utf8mb4",
    local_infile=True,  # 必须在服务端和客户端同时开启
)

for f in csv_files:
    code = os.path.basename(f).replace(".csv", "")
    with conn.cursor() as cur:
        sql = f"""LOAD DATA LOCAL INFILE '{f}'
            INTO TABLE kline
            CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\\n'
            IGNORE 1 LINES
            (trade_date, open, close, high, low,
             volume, amount, amplitude, pct_chg, `change`, turnover)
            SET code = '{code}';"""
        cur.execute(sql)
    conn.commit()
```

**前置条件：** 服务端 `local_infile=ON`
```sql
SET GLOBAL local_infile=1;
```
默认 OFF，需 root 或 SUPER 权限才能开。如果无法开启，用 pandas to_sql 备选方案。

## 备选方案：pandas to_sql（删索引加速，生产验证）

当 `local_infile=OFF` 且没有权限开启时（2026-04-30 实际用此方案）：

```python
from sqlalchemy import create_engine, text

engine = create_engine("mysql+pymysql://stock:stock123@127.0.0.1:3306/stock_kline")

# 1. 删索引（加速 INSERT 10x+）
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE kline_v2 DROP INDEX idx_code"))
    conn.execute(text("ALTER TABLE kline_v2 DROP INDEX idx_date"))
    conn.execute(text("ALTER TABLE kline_v2 DROP INDEX idx_code_date"))

# 2. 小批量导入（5文件/批次，chunksize=1000）
BATCH = 5
for batch in batches:
    combined = pd.concat(batch, ignore_index=True)
    combined.to_sql("kline_v2", engine, if_exists="append", index=False,
                   method="multi", chunksize=1000)

# 3. 重建索引
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE kline_v2 ADD INDEX idx_code (code)"))
    conn.execute(text("ALTER TABLE kline_v2 ADD INDEX idx_date (trade_date)"))
    conn.execute(text("ALTER TABLE kline_v2 ADD INDEX idx_code_date (code, trade_date)"))
```

**关键参数（生产验证值）：**
- `BATCH=5`：5文件/批 ≈ 7500行/批，redo log 不堆积
- `chunksize=1000`：SQLAlchemy 内部分段大小
- 同步模式：`with engine.begin()` 自动 commit
- 用 TCP：`127.0.0.1` 避免 socket 锁问题

## CSV 列名对齐

CSV文件包含中文列名（日期, 开盘, 收盘...）但 `LOAD DATA INFILE` 用 `IGNORE 1 LINES` 跳过表头，直接按顺序映射到英文列。需确保CSV列顺序与SQL字段顺序一致。

CSV列顺序：`trade_date, open, close, high, low, volume, amount, amplitude, pct_chg, change, turnover`

注意 `change` 是 MySQL 保留字，SQL中需用反引号转义。

## redo log 容量问题

### 症状

大事务（2000个文件×1530行=3M行的单次INSERT）会撑爆 InnoDB redo log，触发：
```
[Warning] [MY-014084] [InnoDB] Threads are unable to reserve space in redo log
Consider increasing innodb_redo_log_capacity.
```

### 解决

1. **缩小事务粒度**：每个文件单独提交（`LOAD DATA INFILE` 天然支持）；pandas to_sql 每5文件提交
2. 如果必须大事务，调大 redo log：
```sql
SET GLOBAL innodb_redo_log_capacity = 4294967296;  -- 4GB
```
或写入 `/etc/mysql/mysql.conf.d/mysqld.cnf`：
```
innodb_redo_log_capacity = 4G
```

### 崩溃恢复

如果 INSERT 被 `SIGKILL` 打断（`kill -9` 或进程崩溃），MySQL 重启时 InnoDB 会做崩溃恢复：
- 回滚未提交事务（时间取决于事务大小，3M行约3-5分钟）
- 系统状态显示 `activating (start)` 直到恢复完成
- 恢复期间所有查询/DDL卡在 `Waiting for table metadata lock`
- 用 `systemctl kill -s SIGKILL mysql` 无效——必须等待恢复完成

### 恢复期间的元数据锁排查与清除

大事务被 kill 后，InnoDB 元数据锁可能残留在 table/database 层面，形成**锁链**（一个 COUNT 阻塞 DROP TABLE，DROP TABLE 阻塞 CREATE TABLE，CREATE TABLE 阻塞后续所有连接）。

**症状：** `DROP TABLE` / `CREATE TABLE` / `TRUNCATE` 全部卡死
```
mysql> SHOW FULL PROCESSLIST;
Id  User  Host    db          Command  Time  State
17  stock localhost stock_kline Query   140   Waiting for table metadata lock
20  stock localhost NULL       Query   114   Waiting for schema metadata lock
```

**排查与解决：**

1. **检查 stuck queries（用 TCP 绕过 socket 锁）：**
```bash
mysql -ustock -pstock123 -h127.0.0.1 -e "SHOW FULL PROCESSLIST"
```
TCP 连接更可靠——socket 文件本身可能被卡住的连接占据。

2. **批量杀所有阻塞查询（单条 kill 可能因为锁链失败）：**
```bash
mysql -ustock -pstock123 -h127.0.0.1 \
  -e "SELECT CONCAT('KILL ', id, ';') FROM information_schema.PROCESSLIST WHERE db='stock_kline'" \
  | mysql -ustock -pstock123 -h127.0.0.1
```

3. **如果元数据锁 kill 不掉（MCP 服务器僵死连接），换表名跳过：**
```sql
-- 建新表 kline_v2，绕开原 kline 表的 metadata lock
CREATE TABLE kline_v2 LIKE kline;
-- 导入到 kline_v2
-- 完成后 RENAME（RENAME 不会触发 metadata lock 等待）
RENAME TABLE kline TO kline_old, kline_v2 TO kline;
DROP TABLE kline_old;
```

### MCP MySQL 服务器僵死连接

MCP MySQL Server 进程（`npm exec @berthojoris/mcp-mysql-server`）可能在脚本被 SIGKILL 后残留数据库连接，这些连接持有 metadata lock 且无法被 KILL（进程在 D 状态）。

**解决：** 找到并 kill 僵死的 MCP 进程
```bash
ps aux | grep mcp-mysql | grep -v grep | awk '{print $2}' | xargs kill -9
```

注意：这会导致该会话期间 MySQL MCP 工具不可用。优先尝试换表名绕过。

### 根本预防

不做大事务——每文件单独 commit，避免触发 InnoDB redo log 耗尽导致的 metadata lock 连锁反应。

## MySQL 连接方式对比

| 方式 | 命令 | 适用场景 |
|:----|:-----|:---------|
| Unix socket | `mysql -ustock -pstock123` | 默认最快，但 socket 文件可能被锁 |
| TCP | `mysql -ustock -pstock123 -h127.0.0.1` | 绕过 socket 锁，metadata lock 排查时的救命稻草 |
| SQLAlchemy | `"mysql+pymysql://stock:stock123@127.0.0.1:3306/stock_kline"` | 脚本中用 127.0.0.1 避免 socket 问题 |

## 脚本

`~/quant/bulk_import_to_mysql.py` — 全量导入脚本，pandas to_sql（5文件/批，删索引后建索引）。
`~/quant/import_kline_to_mysql.py` — 旧版导入脚本（逐文件+逐行去重检查，更慢）。

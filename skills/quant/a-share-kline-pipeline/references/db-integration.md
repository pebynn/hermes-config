# DB 集成细节 — stock_kline.kline

## 连接信息

- Host: localhost:3306
- User: stock
- Password: stock123
- DB: stock_kline
- Table: kline
- URL: `mysql+pymysql://stock:stock123@localhost:3306/stock_kline`

## 表结构

```sql
CREATE TABLE kline (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  code         VARCHAR(10) NOT NULL,
  trade_date   DATE NOT NULL,
  open         DECIMAL(12,2),
  close        DECIMAL(12,2),
  high         DECIMAL(12,2),
  low          DECIMAL(12,2),
  volume       BIGINT,
  amount       DECIMAL(16,2),
  amplitude    DECIMAL(8,2),
  pct_chg      DECIMAL(8,2),
  `change`     DECIMAL(8,2),   -- MySQL 保留字，需反引号
  turnover     DECIMAL(12,10),
  INDEX idx_code (code),
  INDEX idx_date (trade_date),
  INDEX idx_code_date (code, trade_date)
);
```

`change` 是 MySQL 保留字，SQL 中必须用反引号 ``` `change` ```。

## pymysql 参数占位符

pymysql 不支持 SQLAlchemy 的 `:param` 命名参数风格（`WHERE code = :code` 会报语法错误）。
必须使用 `%(code)s` 风格（如 `WHERE code = %(code)s`）。

例外：`conn.execute(text("..."), params_dict)` 在 SQLAlchemy 2.0 中自动将 `:param` 转为 `%(param)s`，
所以 `text("WHERE code = :code")` 配合 `{"code": "000001"}` 在 `engine.begin()` + `conn.execute()` 路径下可正常工作。
但 `pd.read_sql(sql, conn, params=params)` 路径仍会失败 — pandas 绕过了 SQLAlchemy 的 `:param` 转换层。

坑：`pymysql 1.4.6` + `SQLAlchemy 2.0.49` 组合下，`conn.execute(text("..."), {":param": val})` 可用，
但 `pd.read_sql(text("..."), conn, params={...})` 不可用。

## 中→英列名映射

```python
COL_MAP_CN2EN = {
    "日期": "trade_date", "开盘": "open", "收盘": "close",
    "最高": "high", "最低": "low", "成交量": "volume",
    "成交额": "amount", "振幅": "amplitude", "涨跌幅": "pct_chg",
    "涨跌额": "change", "换手率": "turnover",
}
```

## daily_kline_update.py 的 upsert 模式

```python
def _insert_to_db(df_cn, code):
    with engine.begin() as conn:
        # 1) 尝试 UPDATE
        r = conn.execute(
            text("""UPDATE kline SET open=:o, close=:c, ...
                    WHERE code=:code AND trade_date=:td"""),
            {"o": ..., "c": ..., ..., "code": code, "td": today_str},
        )
        if r.rowcount > 0:
            return True  # 已有 → 更新成功

        # 2) 不存在 → INSERT
        conn.execute(
            text("""INSERT INTO kline (code, trade_date, open, ...)
                    VALUES (:code, :td, :o, ...)"""),
            {...},
        )
```

在同一 `engine.begin()` 事务中完成，原子性保证。

## 重复数据

历史已存在约 74 万组重复行（同一 code + trade_date 出现多次），源于旧版 import 脚本使用 `if_exists='append'` 无去重。
尚未清理（DELETE 操作因数据量大超时中断）。

添加 UNIQUE KEY `uk_code_date (code, trade_date)` 需要先清重。

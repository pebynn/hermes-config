# 涨跌停数据过滤规则

AKShare的 `stock_zt_pool_em` 和 `stock_zt_pool_dtgc_em` 返回的涨跌停数据包含非标准股票，需过滤后才能计数。

## 过滤规则

```python
def is_valid_limit_stock(row):
    """排除北交所、IPO新股、ST、退市等"""
    code = str(row.get("代码", ""))
    name = str(row.get("名称", ""))
    pct = float(row.get("涨跌幅", 0))

    # 北交所/新三板 (920, 8, 4 开头)
    if code.startswith(("8", "920", "4")):
        return False
    # IPO新股 (名称以 N/C 开头)
    if name.startswith(("N", "C")):
        return False
    # ST/退市
    if "ST" in name or "退" in name:
        return False
    # 退市/异常值 (±100%涨跌幅 = 已退市)
    if abs(pct) >= 99:
        return False
    return True
```

## 验证案例 (2026-05-05)

| 数据 | API原始 | 过滤后 | 排除原因 |
|:--|:--|:--|:--|
| 涨停 | 79只 | 78只 | 920125 鸿仕达 (北交所30%涨跌停) |
| 跌停 | 11只 | 9只 | 600965 福成股份 (-100%, 退市) + 603378 亚士创能 (-100%, 退市) |

## 日期格式

涨跌停API要求 `YYYYMMDD` 格式，非 `YYYY-MM-DD`：
```python
date_str.replace("-", "")  # 2026-05-05 → 20260505
```

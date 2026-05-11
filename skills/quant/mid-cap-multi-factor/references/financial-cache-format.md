# 财务缓存数据格式说明

路径: `~/.finquant/cache/financial/{code}.parquet`

## 列名 (中文)

| 列名 | 说明 | 值格式 |
|:-----|:-----|:-------|
| `报告期` | 报告期日期 YYYY-MM-DD | str |
| `基本每股收益` | 每股收益 TTM | str, '0.6700' |
| `每股净资产` | 每股净资产 | str, '23.91' |
| `净资产收益率` | ROE | str, '2.83%' |
| `销售净利率` | 净利率 | str, '41.17%' |
| `营业总收入` | 总收入 | str, '352.77亿' |
| `营业总收入同比增长率` | 营收YoY | str, '4.65%' |
| `净利润` | 净利润 | str, '145.23亿' |
| `净利润同比增长率` | 净利YoY | str, '3.03%' |
| `资产负债率` | 负债率 | str, '91.02%' |
| `扣非净利润` | 扣非净利润 | str, '144.88亿' |
| `扣非净利润同比增长率` | 扣非净利YoY | str, '3.17%' |

## 关键坑点

### 1. 所有值为字符串类型

`dtype=object` (str)，不是 float。直接做数值比较 (`eps_val > 0`) 会触发:
```
TypeError: '>' not supported between instances of 'str' and 'int'
```

**解决**: 使用 `_to_float()` 辅助函数转换:
```python
def _to_float(val) -> Optional[float]:
    if val is None or pd.isna(val):
        return None
    try:
        s = str(val).strip().replace("%", "").replace(",", "")
        if "亿" in s: return float(s.replace("亿", "")) * 1e8
        if "万" in s: return float(s.replace("万", "")) * 1e4
        return float(s)
    except (ValueError, TypeError):
        return None
```

### 2. 列数不一致

不同股票的 parquet 文件列数不同：
- 000001 (平安银行): 27 列 (含 `date`, `eps`, `roe` 等英文备用列)
- 000002 (万科A): 30 列
- 大部分其他股票: 25 列

**解决**: 使用 `col_name in df.columns` 判断而非假设列存在。

### 3. 百分比列需除100

`净资产收益率`='2.83%' → `_to_float()` 返回 2.83，应除100得 0.0283。
`销售净利率`='41.17%' → 返回 41.17，应除100得 0.4117。

### 4. 亿/万后缀列

`净利润`='383.39亿' → `_to_float()` 返回 38339000000.0（已乘1e8）。

### 5. 负值

EPS/净利润/增长率可以为负：
- 万科A 2026-03-31: `基本每股收益`='-0.5', `净资产收益率`='-5.23%'
- EP因子检查 `eps_raw > 0` 会拒绝负EPS，结果为 NaN

### 6. 按报告期排序

数据按报告期升序排列，最后一行是最新报告期。ROE稳定性用所有可用期计算:
```python
roe_vals = [_to_float(v) for v in df["净资产收益率"] if _to_float(v) is not None]
roe_stability = mean(roe_vals) / std(roe_vals)  # if std > 0
```

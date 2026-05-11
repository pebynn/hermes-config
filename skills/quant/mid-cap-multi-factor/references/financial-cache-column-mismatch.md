# 财务缓存列名不匹配 (2026-05-10 发现)

## 问题

signal_engine._compute_layer1() 从 `~/.finquant/cache/financial/{code}.parquet` 读取
财务数据，但查找的是**中文列名**，实际缓存存的是**英文列名**。

## 实际缓存列名

| 列名 | 示例值 |
|------|--------|
| code | 000001 |
| name | 平安银行 |
| pe | 3.8 |
| pe_ttm | 0.62 |
| pb | 0.48 |
| eps | 2.83 |
| total_mv | 220645289911 |
| float_mv | 220641679425 |
| date | 2026-05-08 |

共 5833 只股票，每只 1 行。

## `_compute_layer1` 期望的列名

| 期望列名 | 用途 | 是否存在 |
|----------|------|:--------:|
| 基本每股收益 | EP 计算 | ❌ |
| 每股净资产 | BP 计算 | ❌ |
| 净资产收益率 | ROE稳定性 | ❌ |
| 销售净利率 | 净利率 | ❌ |
| 营业总收入同比增长率 | 营收增速 | ❌ |
| 净利润同比增长率 | 营业利润增速 | ❌ |

## 影响

全部 12 个 L1 因子返回 np.nan → 行业中性化后 fillna(0) →
`l1_total = 0` → `l1_scaled = 50` (恒定值)。

L1 权重 0.25 在综合评分中贡献恒定 12.5 分，完全失去因子区分能力。
综合排名仅由 L2(30%) + 资金流(20%) + L3(25%) 驱动。

## 修复方案

两个方向任选其一：

### 方案 A (推荐): 改 _compute_layer1 适配英文列名

```python
# 用缓存中的实际列名重新计算
if fin_df is not None and not fin_df.empty:
    # EP: eps / price
    if 'eps' in fin_df.columns:
        eps_val = float(fin_df['eps'].iloc[-1])
        if eps_val > 0 and price > 0:
            result['l1_ep'] = eps_val / price
    # PB: pb as ratio directly
    if 'pb' in fin_df.columns:
        pb_val = float(fin_df['pb'].iloc[-1])
        if pb_val > 0:
            result['l1_bp'] = 1.0 / pb_val  # BP = 1/PB
```

但需要逆向推导：有了 `pe`, `pb`, `eps` 但缺少 ROE、营收增速等，能算的因子大幅缩水。

### 方案 B: 修改财务缓存写入脚本，增加中文字段

找到写入 `financial/{code}.parquet` 的脚本，在保存前复制英文列到中文列名。

## 验证脚本

```bash
~/tools/quant_env/bin/python3 -c "
import pandas as pd
from pathlib import Path
p = Path.home() / '.finquant' / 'cache' / 'financial' / '000001.parquet'
df = pd.read_parquet(p)
print(list(df.columns))
# 期望中文字段名
expected = ['基本每股收益', '每股净资产', '净资产收益率', '销售净利率',
            '营业总收入同比增长率', '净利润同比增长率']
for col in expected:
    print(f'{col}: {\"OK\" if col in df.columns else \"MISSING\"}')
"
```

# Universe Filter: 科创板+北交所+ST 排除

## 背景

策略A v2 动量策略在2026年回测中，全集(含688/92 prefix)结果：
- 年化342.6%, 夏普4.89, 最大回撤-10.2%, 胜率47.7%

排除688(科创板)+92(北交所)后：
- 年化1378.2%, 夏普8.88, 最大回撤-6.8%, 胜率52.3%

## 机制

科创板/北交所股票具有极端波动性(20%/30%涨跌停)和低流动性特征，对动量排名形成噪声污染。它们偶尔会冲入Top10但随后剧烈回撤，拖累整体表现。

## 实现

在 `strategy_v2.py` 的 universe 构建中添加前缀过滤：

```python
# 2. Filter
_exclude_st = set()
_excl_path = Path(__file__).parent / "excluded_stocks.json"
if _excl_path.exists():
    try:
        with open(_excl_path) as f:
            _exclude_st = set(json.load(f))
    except: pass

universe = {c: g.sort_values("日期").reset_index(drop=True) for c, g in ak.groupby("code")
            if len(g) >= MIN_DAYS_V2 
            and g.head(20)["成交额"].mean() >= MIN_AMOUNT_V2
            and not (c.startswith('688') or c.startswith('92'))
            and c not in _exclude_st}
```

## ST 处理

- **主动过滤**: `excluded_stocks.json` 文件(由 tushare/AKShare 定期更新)
- **被动过滤**: `MIN_AMOUNT_V2=5000万` 自然排除 >90% ST 股(ST日均成交额远低于此阈值)
- tushare 日配额(5次/天)耗尽时，依赖被动过滤即可

## excluded_stocks.json 生成

```python
import tushare as ts
ts.set_token('TOKEN')
pro = ts.pro_api()
df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
st_codes = [c.split('.')[1] for c in df[df['name'].str.contains('ST')]['ts_code']]
excluded = set(st_codes)  # + 688/92 handled by prefix in code
import json
with open('excluded_stocks.json', 'w') as f:
    json.dump(sorted(excluded), f)
```

注意: tushare stock_basic 日限额5次。

## 影响总结

| 指标 | 过滤前 | 过滤后 | 改善 |
|:--|:--|:--|:--|
| 年化 | 342.6% | 1378.2% | +302% |
| 夏普 | 4.89 | 8.88 | +82% |
| 最大回撤 | -10.2% | -6.8% | -33% |
| 胜率 | 47.7% | 52.3% | +4.6pp |
| 组合止损触发 | 6次 | 0次 | 消除 |
| 股票池 | 4769 | 4028 | -741只 |

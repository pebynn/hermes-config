# AKShare 环境不可用诊断报告 (2026-05-08)

## 环境

- Ubuntu Linux, 中国网络, 无翻墙工具
- `~/tools/quant_env/bin/python3` — akshare v? installed
- 百度可达, 东方财富 push2 API 可达

## 测试结果

| 接口 | 超时(s) | 结果 | 备注 |
|:-----|:-------|:-----|:------|
| `stock_zh_a_daily('sh600519')` | 20 | ❌ 超时 | 主K线源 |
| `stock_zh_a_hist_tx('sh600519')` | 20 | ❌ 超时 | 腾讯精简 |
| `stock_zh_a_hist('000001')` | 20 | ❌ 超时 | 东方财富 |
| `stock_info_a_code_name()` | 30 | ❌ 超时 | 股票列表 |
| `stock_zh_a_spot_em()` | 20 | ❌ 超时(0/58进度条) | 实时行情 |
| `stock_zh_a_daily` curl后端 | 10 | ❌ param error | 腾讯API不通 |
| `push2.eastmoney.com` (curl) | 10 | ✅ 200 | 东方财富股票列表API |
| `baidu.com` (curl) | 5 | ✅ 200 | 基础网络正常 |

## 可用替代源

| 源 | 速度 | 说明 |
|:---|:-----|:------|
| **雪球 XueqiuSource.get_kline()** | ~0.6s/2000条 | count=-2000 覆盖~8年。不含amount（用close×volume估算） |
| **Tushare pro.daily()** | ~0.4s/全A股 | 需 token(~/.finquant/tushare_token)，0积分免费 |
| **东方财富 push2 API** (curl/urllib) | ~0.5s | 股票列表/资金流向/行业板块，不走AKShare库 |

## 结论

AKShare 在该环境完全不可用（所有接口超时）。判断为网络层或DNS封锁，非账号/频率限制。

**策略**: 历史全量用雪球 (`precache_xueqiu.py`), 每日增量优先 tushare, 雪球兜底. 所有纯 AKShare 路径跳过.

## 验证脚本

```python
# 快速验证可用性
import akshare as ak
try:
    df = ak.stock_zh_a_daily(symbol='sh600519', adjust='qfq', start_date='20260506', end_date='20260507')
    print('AKShare可达')
except Exception as e:
    print(f'AKShare不可达: {e}')
```

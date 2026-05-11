# 雪球数据源集成（2026-05-10 升格为主采集备源）

## 背景

雪球 `stock.xueqiu.com` 在2026-05-07首次接入，仅用于交叉验证和反向填充。2026-05-10升级为Sina失败后的主备源，嵌入5个脚本的采集loop。

## 雪球优势

- 无需 `Referer` 头（与Sina `Referer: finance.sina.com.cn` 不同）
- Cookie认证可持久化（`xq_a_token` 约30天）
- 晚间不受东财黑窗影响
- 批量查询 `batch/quote.json` 一次API调用返回所有指数
- K线 `kline.json` 可选丰富指标（PE/PB/PS/PCF/市值）

## 雪球限制

- 需要有效 cookie（`~/.hermes/credentials/xueqiu_cookies.json`）
- cookie 到期（~30天）后需浏览器重新登录
- K线数据粒度仅日级（Sina提供scale=240日内K线）
- `get_kline()` 的 volume 单位为 **股**（非手）

## 字段映射标准

### 实时指数（get_indices_snapshot）

| 雪球字段 | 统一字段 | 转换 |
|---------|---------|------|
| `current` | `index` | 直接使用 |
| `percent` | `change_pct` | 直接使用（已为%） |
| `amount` / 1e8 | `turnover` | 元→亿元 |
| `open` | `open` | 直接使用 |
| `high`/`low` | `high`/`low` | 直接使用 |
| `volume` | `volume` | 直接使用（股） |
| `name` | `name` | 直接使用 |

### K线（get_kline）

| 雪球字段 | Sina格式字段 | 转换 |
|---------|-------------|------|
| `date` | `day` | 字段名替换 |
| `close` | `close` | 直接使用 |
| `volume` | `volume` | `/100` 股→手 |
| `turnover` | (Sina无) | 保留 |

## Xueqiu symbol映射

| 内部key | Sina code | 雪球 symbol |
|---------|-----------|-------------|
| `shanghai` / `sh` | `sh000001` | `SH000001` |
| `shenzhen` / `sz` | `sz399001` | `SZ399001` |
| `cyb` | `sz399006` | `SZ399006` |
| `kc50` | `sh000688` | `SH000688` |

## 集成模式

### collect_data.py（懒加载单例 + 批量采集）

```python
_XQ_SOURCE: Optional[Any] = None

def _get_xueqiu_source():
    global _XQ_SOURCE
    if _XQ_SOURCE is not None:
        return _XQ_SOURCE
    sys.path.insert(0, str(Path.home() / "quant"))
    from xueqiu_kline import XueqiuSource
    _XQ_SOURCE = XueqiuSource()
    return _XQ_SOURCE

def _collect_xueqiu_indices():
    xq = _get_xueqiu_source()
    snap = xq.get_indices_snapshot()
    # snap: {symbol: {name, current, percent, amount, ...}}
    # → 转换为 {key: {name, index, change_pct, turnover, ...}}
```

### data_collector_seo.py（threading并行）

插入到现有3线程并行采集为第4个线程：
```python
def _t4(): xq_idx_r[0] = _collect_xueqiu_indices()
threads = [threading.Thread(target=t) for t in [_t1, _t2, _t3, _t4]]
```

### fallback_pipeline.py（Sina失败后降级）

```python
if any(failed indices):
    xq_idx = fetch_xueqiu_indices()
    for key, entry in xq_idx.items():
        if local entry is missing:
            data["market"][key] = entry
            logger.info("    (源: 雪球 %s)", entry["name"])
```

### generate_charts.py（K线降级）

```python
try:
    data = requests.get(sina_kline_url).json()  # 原Sina逻辑
    if not data:
        raise ValueError("empty")
except:
    xq = XueqiuSource()
    klines = xq.get_kline("SH000001", count=-30)
    data = [{"day": k["date"], "volume": k["volume"]/100} for k in klines]
```

## 验证

每个脚本集成后运行 `py_compile` 验证语法。端到端验证需要有效cookie和网络连通。

# AKShare 晚间 API 不可用 + Sina 兜底方案

## 问题

东方财富 push2/push2his/push2ex 三个核心 API 在晚间（约18:00-次日08:00 北京时间）定期不可用。表现为：

- `stock_board_industry_name_em()` → `RemoteDisconnected: Remote end closed connection without response`
- `stock_market_fund_flow()` → 超时（>60s 无响应）
- `stock_zt_pool_em()` → 同上
- `stock_zh_a_spot_em()` → 同上

但 `stock_zh_index_daily_em()` 和 web 版东方财富（quote.eastmoney.com）正常。

## 根因

东方财富 push2 API 服务器在非交易时段进入维护/降频模式，主动拒绝连接或空响应。TLS握手成功但应用层不返回数据。

## 解决方案

### 短期：跳过 + cron 正常时段执行

cron 定在 15:30（收盘后30分钟），此时 API 必定可用。晚间手动重跑时跳过 API 依赖图表：

```python
# generate_charts.py 的缓存优先模式
if out_path.exists() and out_path.stat().st_size > 1000:
    logger.info("♻️ 使用已有图表: %s", out_path)
    return out_path
```

### 中期：Sina 财经 API 兜底

Sina 财经 API（hq.sinajs.cn）在晚间仍然可用：

**市场数据**：
```bash
curl -s "https://hq.sinajs.cn/list=sh000001,sz399001,sz399006,sh000688" \
  -H "Referer: https://finance.sina.com.cn"
```

**板块数据**（通过个股平均）：
```python
# Sina 行业板块节点
sectors = {
    "电子信息": "new_dzxx", "电子器件": "new_dzqj", ...
}
url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=80&sort=changepercent&asc=0&node={code}"
# 取每个板块80只股票的平均涨跌幅作为板块涨跌幅
```

**数据格式**：
```
上证指数,4135.45,4112.16,4160.17,4166.15,4129.91,...
         close    prev    open    high    low
```

涨跌幅 = (close - prev) / prev × 100

### 已写入 collect_data.py 的方案

`collect_data.py` 当 AKShare 板块/资金流/涨跌停三个 API 全部失败时，自动降级为 Sina 采集。Sina 数据写入 `all_data.json` 的同时更新 `_meta.sources.sectors` 标注来源。

### API 可用窗口

| 时间段 | push2 API | Sina API | 建议 |
|--------|-----------|----------|------|
| 08:00-16:00 | ✅ 正常 | ✅ 正常 | 使用 AKShare（数据更丰富） |
| 16:00-18:00 | ⚠️ 可能降频 | ✅ 正常 | 优先 AKShare，失败降级 Sina |
| 18:00-08:00 | ❌ 不可用 | ✅ 正常 | 使用 Sina 或跳过 |

## 验证命令

```bash
# 测试 push2 API 可用性
timeout 15 python3 -c "import akshare as ak; print(ak.stock_board_industry_name_em().head(1))"

# 测试 Sina API
timeout 10 curl -s "https://hq.sinajs.cn/list=sh000001" -H "Referer: https://finance.sina.com.cn"
```

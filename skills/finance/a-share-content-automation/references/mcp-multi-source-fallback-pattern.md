# stock-sdk-mcp 多源降级与本地缓存回填模式

## 问题

stock-sdk-mcp（腾讯数据源的MCP Server）作为A股数据采集的**首选源**被引入，但MCP服务存在**间歇性不可用**情况：
- MCP server 3次连续失败后进入冷却窗口（~57s）
- kline_with_indicators 等特定端点可能 fetch failed 但其他端点正常
- 晚间时段（19:00-08:00）MCP服务也可能因上游API锁定而不可用

## 降级链

当 MCP 服务不可用时（非单次超时），按以下顺序降级：

```
stock-sdk-mcp (首选)
  → 本地kline缓存 (kline_cache.json, 当日数据可缓存至次日)
  → all_data.json 元数据 (含数据完整性标记)
  → 外部原始数据 (AKShare直接API → Sina → 雪球)
```

## 本地缓存回填模式

### kline_cache.json 缓存

`~/writing-data/raw/YYYY-MM-DD/kline_cache.json` 结构：
```json
{
  "shanghai": [{"date": "2026-05-08", "open": 4163.85, "high": 4183.06, "low": 4154.25, "close": 4179.95, "volume": 133167307000.0}, ...],
  "shenzhen": [...],
  "cyb": [...],
  "kc50": [...]
}
```

**用途**：
- 当 stock-sdk-mcp kline_with_indicators 不可用时，直接读取缓存的60日K线数据
- 用于 generate_charts.py 的 kline.png、capital_flow.png 等依赖历史K线的图表
- 缓存文件由 collect_data.py 创建，每日更新

**限制**：
- 不含MA技术指标（需实时计算）
- 不含板块/资金流向数据
- 当日收盘后15:30之后的数据是最新的，盘前/盘中可能不完整

### all_data.json 元数据检查

`all_data.json` 含 `data_completeness` 和 `_meta.accuracy` 字段，用于判断哪些数据维度完整：

```python
data_completeness = all_data.get("data_completeness", {})
if data_completeness.get("indices"):
    # 指数数据可用
if data_completeness.get("sectors"):
    # 板块数据可用
```

当 `_meta.accuracy.sectors.level = "C"` 时，即使 `data_completeness.sectors = True`，板块数据也是空的（致命的早期bug，已在2026-05-06修复）。

## 手动模式（非cron执行）

当自动化管线出现故障需要手动介入时，遵循以下步骤：

### 步骤

1. **检查数据缓存**：验证 `~/writing-data/raw/YYYY-MM-DD/` 存在且含 all_data.json + kline_cache.json
2. **检查数据完整性**：读 all_data.json 的 `data_completeness` 和 `_meta.accuracy`，确认哪些维度可用
3. **生成图表**：调用 `generate_charts.py --date 2026-05-08`（用缓存K线数据）
4. **验证图表输出**：检查 `~/writing-data/charts/YYYY-MM-DD/kline.png` 存在且非空
5. **写作**：手动加载 a-share-content-automation skill，参考 all_data.json 的涨停池数据撰写章节
6. **AI写作规避**：写作完成后参考 avoid-ai-writing skill 对中文AI-ism做自查：
   - 检查\"高达\"\"飙升至\"\"领涨全场\"\"从历史经验看\"\"积极信号\"\"投资者可关注\"等
   - 确保所有数字与数据源一致（逐项核对，不依赖AI记忆）
   - 第4节标题必须是\"关注方向\"，全文不可出现\"建议\"二字

### 数据缺失时的处理

| 缺失维度 | 替代方案 |
|:---------|:---------|
| 板块涨跌 | 从涨停股池的 industry 字段推断热点方向 |
| 主力资金 | 标注\"晚间数据不可用\"，明早补充 |
| K线历史 | 使用 kline_cache.json（60日K线） |
| 个股行情 | 使用涨停股池数据（zt_pool）+ kline_cache |

## MCP服务恢复确认

```bash
# 测试stock-sdk-mcp连通性
hermes mcp call stock-sdk get_zt_pool '{"date": "2026-05-08", "type": "zt"}'

# 检查MCP server状态
hermes mcp status
```

## 历史案例：2026-05-08

**症状**：stock-sdk-mcp kline_with_indicators fetch failed（3次失败），但 get_zt_pool 正常
**处理**：
1. 从 `~/writing-data/raw/2026-05-08/kline_cache.json` 读取60日K线
2. 从 `~/writing-data/raw/2026-05-08/all_data.json` 读取涨停股池（98家涨停，2家跌停）+ 指数数据
3. 手动生成 kline.png + market_breadth.png（深色主题，红涨绿跌）
4. matplotlib 使用 Noto Sans CJK SC 字体，FontProperties(fname=路径) 方式指定
5. 资金流向数据缺失 → 标注\"晚间不可用，待补充\"
6. 板块涨跌数据缺失 → 从涨停股池行业分布推断热点（通信设备>通用设备>汽车零部件）

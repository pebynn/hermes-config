# Xueqiu (雪球) 备用数据源

> 发现日期: 2026-05-07
> 重要性: 晚间 AKShare 不可用时的第三个备选源（AKShare → Sina → 雪球）

## 核心价值

| 特性 | AKShare(东财) | Sina 备用 | **雪球** |
|:--|:--|:--|:--|
| 晚间可用(19:00-08:00) | ❌ | ✅ 仅指数 | ✅ **全可用** |
| 个股日K线 | ✅ | ❌ | ✅ |
| PE/PB/市值/PS/PCF | ❌ | ❌ | ✅ |
| 四大指数实时行情 | ✅ (日间) | ✅ | ✅ |
| 成本 | 免费 | 免费 | **免费**(需cookie) |

## Cookie要求

必须包含完整登录态cookie（非仅 xq_a_token）：
- **xq_a_token**：访问令牌
- **xq_r_token**：刷新令牌
- **xq_id_token**：JWT认证令牌
- **xq_is_login**：登录标记（值="1"）
- **u**：用户ID
- **WAF cookie**：ssxmod_itna, ssxmod_itna2（阿里云WAF通过后自动设置）
- 其他辅助：acw_tc, smidV2, cookiesu, device_id, remember

导入方式：登录雪球 → F12 → Application → Cookies → 全选复制 → 存为 `~/.hermes/credentials/xueqiu_cookies.json`

有效期约30天，需定期手动刷新。

## 已验证API

### 1. K线数据 (chart/kline.json)

```
GET https://stock.xueqiu.com/v5/stock/chart/kline.json
Params:
  symbol=SH600519       # 个股或指数代码
  period=day            # day/week/month
  begin=<timestamp_ms>  # 起始时间戳(ms)
  type=before           # before=向前取
  count=-20             # 负数=取最近N条
  indicator=kline,pe,pb,ps,pcf,market_capital  # 个股含估值指标
```

**个股返回格式**（24字段）：
```
[0] timestamp (ms)    [6] 涨跌额          [12] PE_TTM
[1] 成交量(股)        [7] 涨跌幅%          [13] PB
[2] 开盘              [8] 振幅%            [14] PS_TTM
[3] 最高              [9] 成交额(元)       [15] PCF_TTM
[4] 最低              [10-11] 未知         [16] 总市值
[5] 收盘              ...                 [17-23] 其他
```

**指数返回格式**（12字段）：
```
[0] timestamp [1] 成交量 [2] 开盘 [3] 最高 [4] 最低
[5] 收盘 [6] 涨跌额 [7] 涨跌幅% [8] 振幅% [9] 成交额
[10-11] 未知
```

### 2. 批量实时行情 (batch/quote.json)

```
GET https://stock.xueqiu.com/v5/stock/batch/quote.json
Params:
  symbol=SH000001,SZ399001,SZ399006,SH000688
```

**返回格式**：
```json
{
  "data": {
    "items": [
      {
        "market": {"status": "未开盘", ...},
        "quote": {
          "symbol": "SH000001",
          "name": "上证指数",
          "current": 4160.17,
          "percent": 1.17,
          "chg": 48.01,
          "open": ...,
          "high": ...,
          "low": ...,
          "volume": ...,
          "amount": ...,
          "amplitude": ...,
          "high52w": ...,
          "low52w": ...,
          "avg_price": ...,
          "float_market_capital": ...
        }
      }
    ]
  }
}
```

### 3. 单股实时行情 (quote.json)

仅支持单个symbol，多symbol返回空。不推荐使用，用 batch/quote.json 代替。

## 集成模块

模块路径：`~/quant/xueqiu_kline.py`（双域共享基础设施，2026-05-07 从 writing-domain 迁移）
- writing-domain：`collect_data.py` 通过 `sys.path.insert(0, "~/quant/")` import
- 原位置：`~/.hermes/profiles/writing-domain/skills/a-share-data-collector/scripts/xueqiu_kline.py`（symlink → ~/quant/xueqiu_kline.py）
- finance-domain：未来通过同路径 import 复用

⚠️ 历史陷阱（2026-05-07 修复）：初版文件仅放在 writing-domain 目录，collect_data.py 从 `~/quant/` import 失败，导致3-way交叉验证从未生效。迁移到 `~/quant/` 后修复。

CLI使用：
```bash
# 健康检查
python3 xueqiu_kline.py --health

# 四大指数快照
python3 xueqiu_kline.py --snapshot

# 个股/指数K线
python3 xueqiu_kline.py --symbol SH600519 --count -10
```

## 交叉验证集成

晚间的三级降级链：
```
AKShare (push2) → 超时30s → Sina (仅指数) → 缺失 → 雪球 (全维度)
```

写入 `all_data.json` 的 `_cross_validation` 字段，与Sina验证同级：
```json
{
  "_cross_validation": {
    "indices": {"source": "Sina Finance", ...},
    "xueqiu": {
      "source": "Xueqiu (stock.xueqiu.com)",
      "status": "ok",
      "indices": {"SH000001": {"close": 4160.17, "change_pct": 1.17}, ...}
    }
  }
}
```

## 不能做的事

- **雪球文章自动发布**：React前端反自动化检测拦截Playwright点击。已验证：cookie登录成功、编辑器可见、填写成功，但点击"发布"按钮被React事件拦截。降级方案：自动保存Markdown备份到 `~/writing-data/xueqiu-backups/`，手动发布。
- **无cookie访问**：所有API需要有效认证cookie。未登录状态下K线接口仍返回200但数据为空。

## 双域共享

xueqiu_kline.py 应为双域共享基础设施（当前在writing-domain下）：
- **writing-domain**：晚间降级数据源 + 交叉验证第三源
- **finance-domain**：晚间K线更新替代源（daily_kline_update.py降级）

迁移建议：提升到 `~/quant/xueqiu_kline.py` 或 `~/tools/xueqiu_kline.py`，双域通过 Python import 或 subprocess 调用。

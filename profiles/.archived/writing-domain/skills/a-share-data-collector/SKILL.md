---
name: a-share-data-collector
description: A股每日收盘数据采集技能 - 采集大盘/板块/资金流/个股数据
version: 1.0.0
author: Hermes
license: MIT
related_skills: [a-share-review-writer]
scripts: [collect_data.py]
---

# A股每日收盘数据采集技能

每日收盘后自动采集A股核心数据，为复盘写作提供数据支撑。

---

## 触发条件

- 每日15:00 A股收盘后
- 用户主动请求："采集今日A股数据"
- 域主代理数据流编排

---

## 执行流程

### Step 1: 确定采集日期
1. 确认当天是否为交易日（排除周末/节假日）
2. 确认当前时间是否>15:00（数据已更新）
3. 检查数据目录是否存在

### Step 2: 采集大盘指数数据
使用AKShare获取：
```python
import akshare as ak
import pandas as pd

# 上证指数
sh = ak.stock_zh_index_daily(symbol="sh000001")
# 解释：获取上证综指日K线数据

# 深证成指
sz = ak.stock_zh_index_daily(symbol="sz399001")

# 创业板指
cy = ak.stock_zh_index_daily(symbol="sz399006")

# 科创50
kc = ak.stock_zh_index_daily(symbol="sh000688")
```

**提取指标**：
| 指标 | 说明 |
|------|------|
| 收盘价 | 当日收盘点位 |
| 涨跌幅 | (收盘-昨收)/昨收 |
| 成交量 | 当日总成交量 |
| 成交额 | 当日总成交额 |

### Step 3: 采集资金流向数据
```python
# 北向资金
north_flow = ak.stock_hsgt_north_net_flow_in_em()

# 主力资金（近5日）
main_force = ak.stock_individual_fund_flow(stock="sh600000", market="sh")

# 行业资金流向
sector_flow = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流向")
```

**提取指标**：
| 指标 | 说明 |
|------|------|
| 北向净流入 | 沪股通+深股通 |
| 主力净流入 | 超大单+大单 |
| 行业流入Top5 | 资金净流入排名前5行业 |
| 行业流出Top5 | 资金净流出排名前5行业 |

### Step 4: 采集板块热点数据
```python
# 涨幅榜板块（行业板块）
top_sectors = ak.stock_board_industry_name_em()

# 概念板块涨幅
concept_sectors = ak.stock_board_concept_name_em()

# 涨停股
limit_up = ak.stock_zt_pool_em(date="YYYYMMDD")

# 跌停股
limit_down = ak.stock_zt_pool_em(date="YYYYMMDD", type="跌停")
```

**提取指标**：
| 指标 | 说明 |
|------|------|
| 行业涨幅Top5 | 板块名称+涨幅+领涨股 |
| 概念涨幅Top5 | 概念板块+涨幅 |
| 涨停股列表 | 按板块分类 |
| 跌停股列表 | 按板块分类 |

### Step 5: 采集个股亮点数据
```python
# 成交额排名
volume_rank = ak.stock_individual_fund_flow(stock="rank", market="all")

# 换手率排名
# 使用实时行情数据
real_time = ak.stock_zh_a_spot_em()
```

**提取指标**：
| 指标 | 说明 |
|------|------|
| 成交额Top10 | 个股名称+成交额 |
| 换手率Top10 | 个股+换手率 |
| 振幅Top10 | 个股+振幅 |

### Step 6: 复用现有量化工具
```bash
# 使用已有信号引擎
cd ~/quant && python daily_signal_report.py --date YYYY-MM-DD

# 资金流因子
cd ~/quant && python capital_flow_factors.py --date YYYY-MM-DD
```

**可利用的现有资产**：
| 资产路径 | 功能 | 适用性 |
|----------|------|--------|
| ~/quant/signal_engine.py | 12因子+缠论二买信号 | 复盘信号参考 |
| ~/quant/daily_signal_report.py | 全A信号日报 | 板块/个股信号 |
| ~/quant/precache_kline.py | K线数据管线 | 指数日K数据 |

### Step 7: 保存数据
保存到 ~/writing-data/raw/YYYY-MM-DD/
```python
import json, csv

# 按类型保存为JSON/CSV
data = {
    "index": index_data,
    "capital_flow": flow_data,
    "sectors": sector_data,
    "top_stocks": stock_data,
    "signals": signal_data,
    "collect_time": "2026-05-05 15:30",
    "data_sources": ["akshare", "eastmoney", "quant_engine"]
}

with open(f"../writing-data/raw/{date}/all_data.json", "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 工具链

| 工具 | 用途 |
|------|------|
| terminal | 运行Python数据采集脚本 |
| execute_code | 数据清洗/结构化 |
| write_file | 保存原始数据JSON |

---

## 输出规范

### 必需输出
- 原始数据JSON文件，包含：
  - 大盘指数（4个指数）
  - 北向/主力资金流
  - 行业板块Top5涨跌
  - 涨跌停股列表
  - 成交额/换手率排名

### 数据格式
```json
{
  "index": {
    "上证指数": {"close": 3350.52, "change_pct": 0.85, "volume": 3.2e10, "amount": 4200e8},
    "深证成指": {"close": 11200.35, "change_pct": 1.20, "volume": 4.5e10, "amount": 5600e8},
    "创业板指": {"close": 2280.18, "change_pct": 1.45, "volume": 1.8e10, "amount": 2800e8},
    "科创50": {"close": 1080.22, "change_pct": 0.60, "volume": 0.5e10, "amount": 800e8}
  },
  "capital_flow": {
    "north_net_inflow": 35.2,
    "main_force_net_inflow": -25.8,
    "sector_inflow_top5": [...],
    "sector_outflow_top5": [...]
  },
  "sectors": {
    "industry_top5": [...],
    "concept_top5": [...]
  },
  "top_stocks": {
    "limit_up": [...],
    "limit_down": [...],
    "volume_top10": [...],
    "turnover_top10": [...]
  }
}
```

---

## 错误处理

### 数据源不可用
1. AKShare接口异常 → 切换东方财富API
2. EastMoney API异常 → 使用TuShare备用
3. 全部不可用 → 使用最近交易日数据+提示

### 部分数据缺失
1. 标注缺失字段
2. 使用历史均值填充（需要标注）
3. 通知用户数据不完整

### 非交易日
1. 检测是否为非交易日
2. 直接跳过采集
3. 输出提示："今日非交易日，无数据采集"

---

## 复用现有quant工具

本技能应尽量复用~/quant/目录下的现有资产：

```bash
# 信号报告
python3 ~/quant/daily_signal_report.py --output-format json

# 资金流数据（需确认路径）
# python3 ~/quant/capital_flow_factors.py --date YYYY-MM-DD

# K线数据
python3 -c "
import pandas as pd
import akshare as ak
index_daily = ak.stock_zh_index_daily(symbol='sh000001')
print(index_daily.tail(2).to_json(orient='records'))
"
```

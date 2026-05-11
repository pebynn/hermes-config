# 数据采集协议

## 数据源优先级

| 数据源 | 优先级 | 成本 | 覆盖范围 | 说明 |
|--------|--------|------|----------|------|
| AKShare | 1（最高） | 免费 | A股全市场 | 官方推荐，数据完整 |
| 东方财富API | 2 | 免费 | 实时行情/资金流 | 补充实时数据 |
| TuShare | 3 | 免费/收费 | 历史数据/财务 | 高级功能需付费 |

---

## 每日采集流程（交易日15:30）

### 阶段1：大盘核心数据

**采集时间**：交易日15:30

**数据项**：

#### 指数数据
```python
import akshare as ak

# 上证指数
sh_index = ak.stock_zh_index_daily(symbol="sh000001")
# 深证成指
sz_index = ak.stock_zh_index_daily(symbol="sz399001")
# 创业板指
cyb_index = ak.stock_zh_index_daily(symbol="sz399006")
# 科创50
kc50_index = ak.stock_zh_index_daily(symbol="sh000688")
```

**输出字段**：
- 指数名称
- 收盘价
- 涨跌幅（%）
- 成交量
- 成交额

#### 资金数据
```python
# 北向资金
north_flow = ak.money_flow_hsgt()
# 主力资金
main_flow = ak.money_flow_individual()
# 两市成交额
total_turnover = ak.stock_market_activity_legu()
```

**输出字段**：
- 北向资金净流入/流出（亿）
- 主力资金净流入/流出（亿）
- 两市总成交额（亿）
- 较昨日成交额变化（%）

---

### 阶段2：板块/行业数据

**采集时间**：交易日15:30-15:35

#### 涨幅Top5板块
```python
# 板块涨幅榜
sector_rank = ak.stock_board_industry_name_em()
top5_gainers = sector_rank.nlargest(5, '涨跌幅')
```

**输出字段**：
- 板块名称
- 涨跌幅（%）
- 领涨股代码
- 领涨股名称
- 领涨股涨跌幅（%）

#### 跌幅Top5板块
```python
top5_losers = sector_rank.nsmallest(5, '涨跌幅')
```

**输出字段**：
- 板块名称
- 跌幅（%）
- 领跌股代码
- 领跌股名称
- 领跌股跌幅（%）

#### 行业资金流向
```python
# 行业资金流入Top5
sector_inflow = ak.stock_sector_fund_flow_rank()
top5_inflow = sector_inflow.nlargest(5, '主力净流入')

# 行业资金流出Top5
top5_outflow = sector_inflow.nsmallest(5, '主力净流入')
```

**输出字段**：
- 行业名称
- 主力净流入/流出（亿）
- 净流入占比（%）

---

### 阶段3：个股数据

**采集时间**：交易日15:35-15:45

#### 涨停股（按板块分类）
```python
# 涨停股列表
limit_up = ak.stock_zt_pool_em()
```

**输出字段**：
- 股票代码
- 股票名称
- 所属板块
- 涨幅（%）
- 成交额（亿）
- 首次涨停时间

#### 跌停股
```python
# 跌停股列表（使用专用跌停股池接口）
limit_down = ak.stock_zt_pool_dtgc_em(date="20260505")
# ⚠️ 注意：date为YYYYMMDD格式，非YYYY-MM-DD
```

**输出字段**：
- 股票代码
- 股票名称
- 所属行业
- 跌幅（%）
- 成交额（亿）
- 连续跌停天数

#### 成交额Top10
```python
# 全市场成交额排行
turnover_rank = ak.stock_zh_a_spot_em()
top10_turnover = turnover_rank.nlargest(10, '成交额')
```

**输出字段**：
- 股票代码
- 股票名称
- 成交额（亿）
- 涨跌幅（%）

#### 资金净流入Top10
```python
# 资金净流入排行
inflow_rank = ak.stock_individual_fund_flow_rank()
top10_inflow = inflow_rank.nlargest(10, '主力净流入')
```

**输出字段**：
- 股票代码
- 股票名称
- 主力净流入（亿）
- 涨跌幅（%）

#### 资金净流出Top10
```python
top10_outflow = inflow_rank.nsmallest(10, '主力净流入')
```

**输出字段**：
- 股票代码
- 股票名称
- 主力净流出（亿）
- 涨跌幅（%）

---

## 周末数据汇总流程（周六日15:30）

### 阶段1：扫描本周数据

**扫描范围**：
- 本周一至周五的 `~/writing-data/raw/YYYY-MM-DD/` 目录
- 检查交易日完整性（至少3个交易日）

**扫描逻辑**：
```python
import os
from datetime import datetime, timedelta

# 获取本周一到周五的日期
today = datetime.now().date()
if today.weekday() == 5:  # 周六
    # 本周一是today - 5天
    monday = today - timedelta(days=5)
elif today.weekday() == 6:  # 周日
    # 本周一是today - 6天
    monday = today - timedelta(days=6)
else:
    # 今天是节假日，找上一个周日
    last_sunday = today - timedelta(days=today.weekday() + 1)
    monday = last_sunday - timedelta(days=6)

# 扫描周一到周五的数据目录
week_days = []
for i in range(5):
    day = monday + timedelta(days=i)
    data_dir = f"~/writing-data/raw/{day}"
    if os.path.exists(data_dir):
        week_days.append(day)

# 检查交易日完整性
if len(week_days) < 3:
    print(f"本周交易日不足（{len(week_days)}天），暂不生成周总结")
    sys.exit(0)
```

### 阶段2：统计本周核心指标

#### 指数周涨跌幅
```python
import pandas as pd

# 读取每日指数数据
index_data = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/index_data.json")
    index_data.append(df)

# 合并并计算周涨跌幅
weekly_index = pd.concat(index_data)
weekly_return = (weekly_index.iloc[-1]['close'] - weekly_index.iloc[0]['close']) / weekly_index.iloc[0]['close'] * 100
```

#### 每日成交额变化趋势
```python
# 读取每日成交额
turnovers = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/market_data.json")
    turnovers.append(df['total_turnover'])

# 计算变化趋势
turnover_series = pd.Series(turnovers)
turnover_trend = turnover_series.pct_change().mean() * 100  # 平均日变化率
```

#### 北向资金周净流入/流出
```python
# 累计本周北向资金
north_flows = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/capital_flow.json")
    north_flows.append(df['north_flow'])

weekly_north_flow = sum(north_flows)
```

#### 主力资金整体流向
```python
# 累计本周主力资金
main_flows = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/capital_flow.json")
    main_flows.append(df['main_flow'])

weekly_main_flow = sum(main_flows)
```

### 阶段3：识别本周最热方向

#### 统计涨幅Top10板块出现频率
```python
from collections import Counter

# 读取每日涨幅Top10板块
all_top_sectors = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/sector_data.json")
    top10 = df.nlargest(10, '涨跌幅')['板块名称'].tolist()
    all_top_sectors.extend(top10)

# 统计出现频率
sector_freq = Counter(all_top_sectors)
hot_sectors = sector_freq.most_common(10)
```

#### 资金流入最多的行业
```python
# 读取每日行业资金流向
all_sector_flows = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/sector_flow.json")
    all_sector_flows.append(df)

# 合并并统计
weekly_sector_flows = pd.concat(all_sector_flows).groupby('行业名称')['主力净流入'].sum()
top_inflow_sectors = weekly_sector_flows.nlargest(5)
```

#### 涨停股最多的概念板块
```python
# 读取每日涨停股
all_limit_up = []
for day in week_days:
    df = pd.read_json(f"~/writing-data/raw/{day}/limit_up.json")
    all_limit_up.append(df)

# 统计概念板块涨停股数
weekly_limit_up = pd.concat(all_limit_up)
concept_counts = weekly_limit_up.groupby('概念板块').size()
top_concepts = concept_counts.nlargest(5)
```

#### 综合判断本周最热方向
```python
# 综合评分
def calculate_hot_score(sector):
    score = 0
    # 出现频率得分（权重40%）
    freq = sector_freq.get(sector, 0)
    score += freq * 0.4
    # 资金流入得分（权重40%）
    inflow = weekly_sector_flows.get(sector, 0)
    score += inflow * 0.4
    # 涨停股数得分（权重20%）
    limit_count = concept_counts.get(sector, 0)
    score += limit_count * 0.2
    return score

# 计算所有候选板块的得分
candidate_sectors = set(sector_freq.keys()) | set(weekly_sector_flows.keys()) | set(concept_counts.keys())
sector_scores = {sector: calculate_hot_score(sector) for sector in candidate_sectors}

# 排序并选出Top2
hot_directions = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)[:2]
```

---

## 数据保存规范

### 目录结构

```
~/writing-data/
├── raw/                 # 原始数据
│   └── YYYY-MM-DD/
│       ├── index_data.json        # 指数数据
│       ├── capital_flow.json      # 资金流数据
│       ├── sector_data.json       # 板块数据
│       ├── sector_flow.json       # 板块资金流
│       ├── limit_up.json          # 涨停股
│       ├── limit_down.json        # 跌停股
│       ├── turnover_rank.json     # 成交额排行
│       ├── inflow_rank.json       # 资金流入排行
│       └── outflow_rank.json      # 资金流出排行
├── analysis/            # 分析报告
│   └── YYYY-MM-DD-analysis.md
├── drafts/              # 复盘文章
│   ├── YYYY-MM-DD-每日复盘.md
│   └── YYYY-MM-DD-周总结.md
└── publish-logs/        # 发布日志
    ├── YYYY-MM-DD-publish.log
    └── YYYY-MM-DD-weekly-analysis.log
```

### JSON格式规范

#### index_data.json
```json
{
  "date": "2026-05-05",
  "indices": [
    {
      "name": "上证指数",
      "code": "sh000001",
      "close": 3234.56,
      "change": 1.23,
      "turnover": 5200.5
    },
    {
      "name": "深证成指",
      "code": "sz399001",
      "close": 10567.89,
      "change": -0.45,
      "turnover": 6200.8
    }
  ]
}
```

#### capital_flow.json
```json
{
  "date": "2026-05-05",
  "north_flow": 25.6,
  "main_flow": -18.3,
  "total_turnover": 11401.3,
  "turnover_change": 15.2
}
```

#### sector_data.json
```json
{
  "date": "2026-05-05",
  "top_gainers": [
    {
      "sector": "AI算力",
      "change": 4.56,
      "leader_code": "603019",
      "leader_name": "中科曙光",
      "leader_change": 10.0
    }
  ],
  "top_losers": [
    {
      "sector": "房地产",
      "change": -3.21,
      "leader_code": "000002",
      "leader_name": "万科A",
      "leader_change": -5.02
    }
  ]
}
```

---

## 数据验证协议

### 数据完整性检查

```python
def validate_daily_data(date):
    """验证每日数据完整性"""
    data_dir = f"~/writing-data/raw/{date}"
    required_files = [
        'index_data.json',
        'capital_flow.json',
        'sector_data.json',
        'limit_up.json',
        'limit_down.json'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(f"{data_dir}/{file}"):
            missing_files.append(file)

    if missing_files:
        raise ValueError(f"数据不完整，缺失文件：{', '.join(missing_files)}")

    return True
```

### 数据准确性检查

```python
def validate_data_accuracy(data):
    """验证数据准确性"""
    # 检查涨跌幅范围（-20%到+20%）
    if 'change' in data:
        if abs(data['change']) > 20:
            raise ValueError(f"涨跌幅异常：{data['change']}%")

    # 检查成交额非负
    if 'turnover' in data:
        if data['turnover'] < 0:
            raise ValueError(f"成交额异常：{data['turnover']}")

    # 检查日期格式
    if 'date' in data:
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"日期格式错误：{data['date']}")

    return True
```

### 异常值处理

**策略1：跳过异常数据**
```python
if abs(change) > 20:
    print(f"警告：{name}涨跌幅{change}%超出正常范围，已跳过")
    continue
```

**策略2：使用备用数据源**
```python
try:
    data = ak.stock_zh_index_daily(symbol="sh000001")
except Exception as e:
    print(f"AKShare获取失败，切换到东方财富API")
    data = get_index_from_eastmoney()
```

**策略3：标记异常值**
```python
if abs(change) > 15:
    data['is_anomaly'] = True
    data['anomaly_reason'] = "涨跌幅超过15%"
```

---

## 错误处理

### 网络错误
```python
import time
from requests.exceptions import RequestException

def fetch_with_retry(func, max_retries=3, delay=2):
    """带重试的数据获取"""
    for i in range(max_retries):
        try:
            return func()
        except RequestException as e:
            if i < max_retries - 1:
                print(f"网络错误，{delay}秒后重试... ({i+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise Exception(f"数据获取失败，已重试{max_retries}次") from e
```

### 数据格式错误
```python
import json

def load_json_safely(file_path):
    """安全的JSON加载"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Exception(f"JSON格式错误：{file_path}") from e
    except FileNotFoundError:
        raise Exception(f"文件不存在：{file_path}")
```

### 数据源不可用
```python
def get_data_with_fallback(primary_func, fallback_func, data_name):
    """主备数据源切换"""
    try:
        return primary_func()
    except Exception as e:
        print(f"主数据源获取{data_name}失败：{e}")
        print("切换到备用数据源...")
        return fallback_func()
```

---

## 性能优化

### 并行采集
```python
from concurrent.futures import ThreadPoolExecutor

def collect_data_parallel():
    """并行采集数据"""
    tasks = [
        fetch_index_data,
        fetch_capital_flow,
        fetch_sector_data,
        fetch_limit_stocks
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda f: f(), tasks))

    return results
```

### 数据缓存
```python
import pickle
from datetime import datetime, timedelta

def get_cached_data(key, cache_duration=3600):
    """获取缓存数据"""
    cache_file = f"~/.cache/hermes/{key}.pkl"

    try:
        with open(cache_file, 'rb') as f:
            cached = pickle.load(f)

        # 检查缓存是否过期
        cache_time = cached['timestamp']
        if datetime.now() - cache_time < timedelta(seconds=cache_duration):
            return cached['data']
    except (FileNotFoundError, KeyError, EOFError):
        pass

    return None
```

### 增量更新
```python
def incremental_update(existing_data, new_data, key_field='date'):
    """增量更新数据"""
    existing_dates = {item[key_field] for item in existing_data}
    new_items = [item for item in new_data if item[key_field] not in existing_dates]

    return existing_data + new_items
```

---

## 监控与告警

### 数据采集监控
```python
def monitor_data_collection():
    """监控数据采集状态"""
    today = datetime.now().strftime('%Y-%m-%d')
    data_dir = f"~/writing-data/raw/{today}"

    # 检查数据完整性
    required_files = ['index_data.json', 'capital_flow.json', 'sector_data.json']
    missing = [f for f in required_files if not os.path.exists(f"{data_dir}/{f}")]

    if missing:
        send_alert(f"数据采集不完整，缺失文件：{', '.join(missing)}")

    # 检查数据时效性
    file_mtime = os.path.getmtime(f"{data_dir}/index_data.json")
    data_time = datetime.fromtimestamp(file_mtime)
    if datetime.now() - data_time > timedelta(hours=2):
        send_alert(f"数据过期，采集时间：{data_time}")
```

### 质量告警
```python
def check_data_quality(data):
    """检查数据质量"""
    issues = []

    # 检查异常值
    for item in data:
        if abs(item.get('change', 0)) > 20:
            issues.append(f"{item['name']}涨跌幅异常：{item['change']}%")

    # 检查数据一致性
    if 'total_turnover' in data:
        expected = data['sh_turnover'] + data['sz_turnover']
        if abs(data['total_turnover'] - expected) > 100:
            issues.append(f"成交额不一致：总计{data['total_turnover']}，预期{expected}")

    if issues:
        send_alert(f"数据质量问题：{'; '.join(issues)}")
```

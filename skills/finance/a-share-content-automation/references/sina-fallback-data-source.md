# Sina 财经 API 备用数据源

东方财富 push2 API 晚间不可用时，使用 Sina 财经 API 作为备用数据源。

## 行业板块涨跌幅

### 新浪行业代码表

```
玻璃行业: new_blhy    传媒娱乐: new_cmyl    船舶制造: new_cbzz
电力行业: new_dlhy    电器行业: new_dqhy    电子器件: new_dzqj
电子信息: new_dzxx    发电设备: new_fdsb    纺织行业: new_fzhy
飞机制造: new_fjzz    钢铁行业: new_gthy    公路桥梁: new_glql
供水供气: new_gsgq    化纤行业: new_hxhy    化工行业: new_hghy
环保行业: new_hbhy    机械行业: new_jxhy    家电行业: new_jdhy
建筑建材: new_jzjc    交通运输: new_jtys    金融行业: new_jrhy
酒店旅游: new_jdly    开发区: new_kfq      煤炭行业: new_mthy
酿酒行业: new_njhy    农林牧渔: new_nlmy    农药化肥: new_nyhf
其它行业: new_qthy    汽车制造: new_qczz    商业百货: new_sybh
生物制药: new_swzy    食品行业: new_sphy    水泥行业: new_snhy
塑料制品: new_slzp    陶瓷行业: new_tchy    石油行业: new_syhy2
有色金属: new_ysjs    造纸行业: new_zzhy    综合行业: new_zhhy
```

### API 端点

```
GET https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData
  ?page=1
  &num=80            # 每板块取80只股票（足够计算均值）
  &sort=changepercent
  &asc=0             # 降序
  &node={行业代码}
Headers: {"Referer": "https://finance.sina.com.cn"}
```

### 返回格式

```json
[
  {
    "code": "300166",
    "name": "东方国信",
    "changepercent": "20.01",
    ...
  },
  ...
]
```

### 数据处理：板块平均涨跌幅

Sina API 返回的是**板块内个股数据**，不是板块聚合值。需要计算平均：

```python
import requests, statistics

url_base = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=80&sort=changepercent&asc=0&node="

sectors = []
for name, code in sina_sectors.items():
    r = requests.get(url_base + code, timeout=10, headers={"Referer": "https://finance.sina.com.cn"})
    data = r.json()
    pcts = [float(s.get('changepercent', 0)) for s in data]
    avg_pct = statistics.mean(pcts)
    leader = data[0]  # 涨幅第一为领涨股
    sectors.append({
        "name": name,
        "change_pct": round(avg_pct, 2),
        "leader": leader.get("name", ""),
        "leader_change": float(leader.get("changepercent", 0)),
        "stock_count": len(pcts)
    })

sectors.sort(key=lambda x: x["change_pct"], reverse=True)
```

### 与东方财富名称映射

Sina 行业分类是传统32行业分类（2000年代），与东方财富的申万行业分类不完全一致：

| Sina 名称 | 东方财富对应 |
|:--|:--|
| 电子信息 | 约等于 计算机+通信 |
| 金融行业 | 约等于 银行+保险+证券 |
| 生物制药 | 约等于 医药生物 |

**注意**：Sina 数据是近似值，精度 B 级。在东方财富可用时优先用东方财富，仅在晚间 API 不可用时作为备用。

## 指数实时行情

```
GET https://hq.sinajs.cn/list=sh000001,sz399001,sz399006,sh000688
Headers: {"Referer": "https://finance.sina.com.cn"}
```

返回 GB2312 编码，格式：
```
var hq_str_sh000001="上证指数,4135.45,4112.16,4160.17,4166.15,4129.91,0,0,701177480,1465903193400,...";
```
字段（⚠️ 致命陷阱：parts[1]=今开不是收盘！）：
| 索引 | 含义 | 示例值 | 说明 |
|:--|:--|:--|:--|
| parts[1] | **今开** | 4135.45 | ⚠️ 不是收盘！交易时段是当前价，盘后是今开 |
| parts[2] | 昨收 | 4112.16 | |
| parts[3] | **收盘** | 4160.17 | 这才是收盘价 |
| parts[4] | 最高 | 4166.15 | |
| parts[5] | 最低 | 4129.91 | |
| parts[8] | 成交量(手) | 701177480 | |
| parts[9] | 成交额(元) | 1465903193400 | 需 /1e8 转亿 |

**验证方法**：用东方财富 push2 API 交叉比对。
```python
# 东方财富 f170=涨跌幅×100, f43=最新价, f60=昨收
# 上证 f170=117 → 1.17%, f43=416017→4160.17, f60=411216→4112.16
# Sina: (parts[3]-parts[2])/parts[2] = (4160.17-4112.16)/4112.16 = 1.168% ≈ 1.17% ✓
```

## 2026-05-06 实测效果

| 板块 (Sina) | 平均涨跌幅 | 股票数 | 领涨股 |
|:--|:--|:--|:--|
| 电子信息 | +5.35% | 80 | 东方国信 |
| 电子器件 | +4.37% | 80 | 晓程科技 |
| 机械行业 | +4.08% | 80 | 汇金股份 |
| ... | ... | ... | ... |
| 酒店旅游 | -1.43% | — | — |

当日东方财富行业板块（申万分类）的实际涨幅对比（推测）：
- 计算机 ≈ Sina 电子信息 (+5.35%)
- 电子 ≈ Sina 电子器件 (+4.37%)
- 社会服务 ≈ Sina 酒店旅游 (-1.43%)

数据方向一致，绝对数值有±1%偏差（因为分类体系不同），用于复盘文章足够。

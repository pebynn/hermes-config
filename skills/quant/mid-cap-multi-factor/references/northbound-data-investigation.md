# 北向资金个股数据源调查 (2026-05-01)

## 调查目的

为L4量化层寻找个股级北向资金每日净买额/成交额数据。

## 测试环境

- akshare 1.18.58
- Python 3.12 (quant_env)
- 测试日期: 2026-05-01
- 测试标的: 600519 (贵州茅台), 000001 (平安银行)

## 已失效的接口

| 接口 | 测试日期范围 | 报错/现象 | 根因 |
|:-----|:-----------|:---------|:-----|
| `stock_hsgt_individual_detail_em` | 20260401~20260429 | `TypeError: 'NoneType' object is not subscriptable` | 东方财富数据源停止发布个股逐日明细 |
| `stock_hsgt_individual_em` | A股600519 | 无数据（仅港股通00700腾讯有数据） | A股北向持仓数据已停更 |
| `stock_hsgt_hold_stock_em` | 沪股通 今日排行 | 返回1336行但数据停滞于**2024-08-16** | 东方财富北向持仓页面不再更新 |
| `stock_hsgt_board_rank_em` | 今日增持 | `'NoneType' object is not subscriptable` | 同源问题 |
| `stock_hsgt_stock_statistics_em` | 多种symbol | 0行返回 | 数据源废弃 |
| `stock_hsgt_institution_statistics_em` | 沪股通 | 返回None | 机构统计接口失效 |
| EastMoney datacenter `RPT_MUTUAL_STOCK_HSGTNORTHFLOW` | — | `报表配置不存在` | 报表已下线 |
| EastMoney push2his `kamt.rtui` | — | 404 | 端点不存在 |

## 仍可用的接口

| 接口 | 类型 | 覆盖 | 说明 |
|:-----|:----|:-----|:-----|
| `stock_hsgt_hist_em` | 市场级汇总 | 沪股通/深股通每日总额 | 2014-11至今，最新几天净买额为NaN（数据延迟） |
| `stock_hsgt_fund_flow_summary_em` | 市场级汇总 | 沪股通/深股通/港股通当日汇总 | 最新数据可用 |
| `stock_hsgt_fund_min_em` | 分钟级汇总 | 盘中实时 | 可用但收盘后数据归零 |
| 东方财富 clist BK0707 | 板块成员列表 | 1532只北向标的 | 只返回代码/名称/涨跌幅，**无净买额字段** |

## 结论

**个股级北向资金净买额数据不可获取。** 原因：香港交易所改变了数据披露方式或东方财富停止维护北向个股明细页面。AKShare 无法从源头获取数据。

### 可用的替代

| 数据类型 | 可用性 | 粒度和用途 |
|:--------|:-----|:----------|
| 融资融券个股明细 | ✅ 完全可用，4000只 | **L4主力数据源** |
| 北向市场级汇总 | ✅ 可用 | L4宏观环境加成（+5%） |
| 北向板块成员 | ✅ 1532只列表 | 判断个股是否在北向池中 |

## L4策略调整

基于调查结果，L4方案修正为：

- **核心数据源**: 融资融券（个股级，4指标，0-100分）
- **北向降级**: 当日北向净流入>0 → L4总分×1.05（仅宏观环境信号）
- **放弃**: 个股北向净买额不再作为独立因子

## 你可能想知道的

- 东方财富网页 `data.eastmoney.com/hsgt/hsgtDetail/ashareflow/` 仍能显示个股北向数据（JavaScript渲染），但后端 JSON API 已不对外暴露或已废弃
- 香港交易所官网有 CSV 下载，但需要每日手动下载，不适合自动化管线
- AKShare 的港股通个股持仓接口 (`stock_hsgt_individual_em` for 港股) 数据更新正常（测试00700腾讯最新2026-04-30），说明港交所→AKShare的数据链路本身是通的，只是A股方向被关闭了

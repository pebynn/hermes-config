# A股数据源对比（2026-05-05 深度调研）

## 核心结论

writing-domain 复盘管线目前使用 AKShare 完全免费方案，除板块历史涨跌幅和主力资金历史数据外，其余维度均已达标。
`stock_board_industry_hist_em()` 可零成本修复板块历史数据问题。主力资金历史需 Tushare Pro（~600元/年）。

## 数据源总表

| 数据源 | 类型 | 成本 | 指数行情 | 板块涨跌 | 主力资金 | 板块资金 | 涨跌停 | 历史支持 | 适用性 |
|--------|------|------|---------|---------|---------|---------|-------|---------|-------|
| **AKShare** | Python库(东方财富) | 免费 | ★★★ | ★★★ | ★★ | ★★ | ★★★ | 部分 | **主数据源** |
| **Tushare Pro** | Python库(多源) | ~600元/年 | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | 全量 | 资金流补充 |
| **Baostock** | Python库(交易所) | 免费 | ★★★ | ✗ | ✗ | ✗ | ✗ | 全量 | 仅K线备份 |
| **Adata(1nchaos)** | Python库(多源) | 免费 | ★★ | ★★ | ? | ? | ? | 全量 | 潜在备用 |
| **EastMoney直连** | REST API | 免费 | ★★★ | ★★★ | ★★ | ★★ | ★★★ | 全量 | 无文档风险 |
| **Wind** | 专业终端 | 3.98万/年 | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | 全量 | 过度消费 |
| **Choice** | 专业终端 | 1.8万/年 | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | 全量 | 过度消费 |

## 各维度推荐数据源

### 大盘指数
- **最佳**: `ak.stock_zh_index_daily_em(symbol="sh000001")` — 有amount列，全历史
- **备选**: `ak.stock_zh_index_daily(symbol="sh000001")` — 无amount列
- **付费**: Tushare `index_daily` / `index_zh_a_hist` (2000积分)
- **准确性**: 100%（交易所数据）

### 板块涨跌幅（当日+历史）
- **最佳（免费）**: `ak.stock_board_industry_hist_em(symbol="板块名")` — 全历史日K线
- **备选（免费）**: `ak.stock_board_industry_name_em()` — 仅最新排行
- **付费**: Tushare `dc_index_daily` (2000积分)
- **准确性**: 100%（东方财富计算）

### 主力资金（当日）
- **唯一免费**: `ak.stock_market_fund_flow()` — 无date参数，始终最新
- **付费历史**: Tushare `moneyflow_mkt_dc` (6000积分)
- **准确性**: 估算值 B级（东方财富算法，市场公认标准）

### 行业资金流向
- **免费当日**: `ak.stock_sector_fund_flow_rank(indicator="今日")` — 始终最新
- **付费历史**: Tushare `moneyflow_dc` (2000积分)
- **准确性**: 估算值 B级

### 涨跌停
- **最佳**: `ak.stock_zt_pool_em(date="YYYYMMDD")` + `_dtgc_em`
- **过滤规则**: 需排除北交所/IPO新股/ST/退市（见 limit-stock-filtering.md）
- **准确性**: 100%（需过滤后计数）

### 两市合计成交额
- **公式**: 上证成交额 + 深证成交额（从指数日K线取 amount 转亿）
- **准确性**: 100%
- **注意**: `ak.stock_zh_index_daily()` 无amount列，必须用 `stock_zh_index_daily_em`

## 关键限制一览

| 维度 | 当前限制 | 建议方案 |
|------|---------|---------|
| 主力资金历史 | AKShare实时端点，无date参数 | 当日采集OK；周总结用重复检测跳过 |
| 板块历史涨跌幅 | ❌已解决 | `stock_board_industry_hist_em()` 免费修复 |
| 概念板块历史 | 同行业板块问题 | `stock_board_concept_hist_em()` 同模式修复 |
| 行业资金流历史 | AKShare实时端点，无date参数 | 当日采集OK；周总结用末期值 |
| 北向资金 | 2024-08后停更 | 已切主力资金 |
| 涨跌停过滤 | 需手动过滤非标股票 | 已有 is_valid_limit_stock() 函数 |

## 付费数据源决策树

需要主力资金历史数据？
├── 否 → 保持纯AKShare免费方案（足够）
└── 是 → 需要精确周累计资金流？
    ├── 否 → 保持+重复检测（够用）
    └── 是 → Tushare Pro 6000积分 ~600元/年

需要行业资金流历史数据？
├── 否 → 保持纯AKShare免费方案（足够）
└── 是 → Tushare Pro moneyflow_dc 2000积分 ~200元/年

## 收费定价参考

| 产品 | 年费 | 备注 |
|------|------|------|
| Tushare Pro 6000积分 | ~600元 | 个人绰绰有余 |
| Tushare Pro 2000积分 | ~200元 | 部分接口可用 |
| Choice标准版 | 1.8万 | 含AI功能2.9万 |
| iFind标准版 | 1.4万 | 优惠"买一送二" |
| Wind标准版 | 3.98万 | 机构标配 |
| **推荐方案** | **0~600元/年** | **AKShare + 可选Tushare Pro** |

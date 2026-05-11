# 东方财富资金流 + 财务数据缓存管线 (2026-05-08)

## 背景

AKShare 在该环境完全不可用，但东方财富 push2 API 可直连。

## 资金流数据（已验证可用）

### 个股资金流

**API**: `push2.eastmoney.com/api/qt/clist/get`
**字段**: f62(主力净流入), f64(净占比%), f66(超大单), f69(大单), f70(中单), f78(小单), f84(收盘价)
**分页**: 单页最多返回~100条（即使设 pz=5000）。需分页 (pn=1,2,3...) 获取全量
**缓存**: `~/.finquant/cache/fund_flow/fund_flow_{date}.parquet`

脚本:
- `~/quant/precache_fund_flow_financial.py` — 分页+并行拉取（但存在反爬问题）
- `~/quant/precache_fund_flow_full.py` — 逐只 fflow/daykline 方案（被限流，16h完成不可行）

### 反爬行为（2026-05-08 验证）

| 行为 | 详情 |
|:-----|:------|
| clist/get 首次请求 | 第1页正常返回100条（0.3s） |
| clist/get 分页请求 | 第2页起 "Remote end closed connection without response" |
| 恢复时间 | IP 封禁持续 >15分钟 |
| 逐只 fflow/daykline | 连续请求 ~5只后限流至12s/只 |
| 影响范围 | 同一IP的所有push2请求均受影响 |
| 绕过方案 | 1. 换不同排序键(fid)获取多组Top100后去重(~800只) 2. 等IP解封后重试分页 |

**建议**: 全量资金流在当前环境下不可行（东方财富反爬严格）。Top100按主力净流入排序已覆盖最活跃标的。如需全量可考虑付费数据源（Tushare Pro ~600元/年）。

### 行业资金流

**API**: 同上, 但 `fs=m:90+t:2`
**字段**: f62(净流入), f104(指数点位), f105(涨跌幅), f128(成交额), f140(换手率), f136(PE)
**缓存**: `~/.finquant/cache/fund_flow/sector_flow_{date}.parquet`

### 北向资金

**API**: `push2.eastmoney.com/api/qt/kamt.kline/get`
**字段**: klines[0].split(",") → [时间, 沪股通净买入, 深股通净买入, ...]
**缓存**: `~/.finquant/cache/fund_flow/northbound_{date}.parquet`
**注意**: 此 API 晚间可能返回空数据

### 逐只资金流API（备选，已被限流）

**API**: `push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid=1.{code}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55&klt=101&lmt=1`
**返回**: `"2026-05-08,main_flow,retail_flow,mid_flow,large_flow"` (4个float值)
**性能**: 单只 ~0.3s 初始, 连续请求后被限流至~12s/只
**适用**: 少量股票(≤20只)的资金流查询，不适合全量

## 财务数据（已知问题）

### 已验证可用的字段（clist/get）

| 字段 | 含义 | 已验证 |
|:-----|:-----|:-------|
| f9 | PE(动) | ✅ 000001=3.8 正确 |
| f10 | PE_TTM | ✅ |
| f23 | PB | ✅ 000001=0.48 正确 |
| f37 | EPS | ✅ 000001=2.83 正确 |

### 有问题的字段

| 字段 | 期望含义 | 实际值(000001) | 结论 |
|:-----|:---------|:--------------|:-----|
| f38 | 每股净资产 | 104616000.0 | 非每股净资产，数值过大 |
| f40 | ROE | 51784486.51 | 非ROE% |
| f56 | 营收同比% | 2244399.3 | 非百分比 |
| f57 | 净利同比% | 15.6 | 可能正确但单位不明 |

### stock/get 端点（更差）

`push2.eastmoney.com/api/qt/stock/get?secid=1.{code}` 返回的字段映射混乱。
f43=最新价但单位是"分"（137111=1371.11元）。
f55 不是昨收。
**不支持批量查询**（rc=102 当传入多个secid时）。

### 财务数据拉取脚本

- `~/quant/precache_financial_fixed.py` — 纯 clist/get 分页方案，只取 PE/PB/EPS（已验证字段正确）
- 每页100只，5850只全量约59页/2分钟
- 数据写入 `~/.finquant/cache/financial/{code}.parquet`

### 建议方案

1. **PE/PB/EPS**: 使用 clist/get 的 f9/f10/f23/f37，已验证正确
2. **ROE/营收同比/负债率**: 需要从其他API获取
   - tushare fina_indicator: 需要更高积分（当前免费版无权限）
   - 同花顺直连API: 未验证
   - 东方财富 datacenter API: 返回 code=9501（需认证）
3. **当前现状**: 只缓存了 PE/PB/EPS，ROE/营收同比等字段缺失
   - 策略脚本(signal_engine)已经内置 fallback：缺财务数据时静默跳过对应因子

## 东方财富 push2 通用注意事项

1. **分页限制**: 无论 pz 设多大，clist/get 单页最多返回~100条。需分页 (pn=1,2,3...)获取全量
2. **分页反爬**: 快速连续分页请求会被封IP（第2页起断连），封禁>15分钟
3. **secid 格式**: 沪市 `1.{code}`, 深市 `0.{code}`（与clist/get中的fs参数不同）
4. **字段编号不一致**: stock/get 的 f43 含义与 clist/get 的 f43 **不同**。不能跨API复用字段映射
5. **日频限制**: 数据盘中实时更新，收盘后冻结。历史日频需 clist/get 的排序参数
6. **晚间可用性**: 东方财富 push2 API 北京时间 19:00-08:00 可能不可用（需验证）
7. **批量查询不可用**: stock/get 不支持批量 secids（返回 rc=102）

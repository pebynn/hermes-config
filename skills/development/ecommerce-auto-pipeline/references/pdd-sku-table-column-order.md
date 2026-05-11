# PDD SKU 表格列顺序 & 字段位置（2026-05-03 验证）

## 验证环境

- 页面: `https://mms.pinduoduo.com/goods/goods_add/index`（中老年女装/套装分类）
- 方法: Playwright headed 模式，提取完整 DOM → `~/PDD/form_structure.json`
- 会话状态: 已登录（auth 复用 `~/.pdd_auth.json`）

## SKU 表格列顺序

SKU 表格容器: `[data-e2e-id="e2e-sku-table"] table.TB_tableWrapper_5-188-0`

| 列 | 标题 | 宽度 | CSS 选择器 (nth-child) | 输入组件类型 | 备注 |
|---|---|---|---|---|---|
| 1 | *库存 | 92px | `td:nth-child(1) input` | 普通文本输入 (IPT_input) | td 有 `quantity is_create` 类 |
| 2 | *拼单价(元) | 150px | `td:nth-child(2) input` | 数字输入 (InputNumber, min=0) | div 有 `sku-beast-price-input-container` 类 |
| 3 | *单买价(元) | 150px | `td:nth-child(3) input` | 数字输入 (InputNumber, min=0) | div 有 `sku-beast-price-input-container` 类 |
| 4 | 规格编码 | 220px | `td:nth-child(4) input` | 普通文本输入 (IPT_input) | |
| 5 | 商品编码 | 140px | `td:nth-child(5) input` | 普通文本输入 (IPT_input) | |
| 6 | 状态 | 80px | `td:last-child` | 非输入（下拉选择"已启用"） | |

## 重要: 列顺序

**第1列 = 库存，第2列 = 拼单价，第3列 = 单买价。**

拼单价和单买价的 DOM 结构完全相同（都是 `div.sku-beast-price-input-container > beast-core-inputNumber`），只能通过 `nth-child(2)` vs `nth-child(3)` 区分。**不能用类选择器区分两者。**

## 全局价格字段

表格下方有一个独立字段:

| 字段 | 选择器 | 规则 |
|---|---|---|
| 商品参考价（市场价/一口价） | `#market_price input[placeholder*="应大于商品最大单买价"]` | 必须 > 所有 SKU 单买价的最大值 |

注意: **没有全局的"拼单价"字段。** 所有价格都在 SKU 表格内逐行填写。

## "单买价至少比拼单价高1元"错误

触发条件:
1. 列顺序写反 — 把单买价的值填到了拼单价列（或反之）
2. 同一个值写了两个列
3. 单买价实际值 < 拼单价实际值（每行独立校验）

## 推荐选择器（稳定版）

```python
SKU_TABLE = '[data-e2e-id="e2e-sku-table"] table'
STOCK_INPUT = '[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child(1) input'
PINTUAN_INPUT = '[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child(2) input'
DANMAI_INPUT = '[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child(3) input'
SPEC_CODE_INPUT = '[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child(4) input'
GOODS_CODE_INPUT = '[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child(5) input'
MARKET_PRICE = '#market_price input[placeholder*="应大于商品最大单买价"]'
```

## 验证脚本

```bash
python3 ~/PDD/inspect_form.py
# 输出保存到 ~/PDD/form_structure.json 和 ~/PDD/form_analysis.json
```

## 页面结构变更历史

| 时间 | 变更 |
|:----|:-----|
| 2026-05前 | 旧入口 `/goods/add`，旧 SKU 表结构 |
| 2026-05-03 | 入口改为 `/goods/category` → 选分类 → `/goods/goods_add/index`，SKU 表使用 beast-core 组件（TB_tableWrapper 类） |

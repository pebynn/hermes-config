# PDD 商品发布表单自动化技术笔记

> 基于 2026-05-03 实战调试，适配 mms.pinduoduo.com 当前版本。
> 当前脚本: `~/PDD/pdd_listing_v3.py` (~1600行)，**双路径：半自动可用 / API全自动待凭证**。

## 已验证可用的功能

| 功能 | 状态 | 技术方案 |
|:-----|:----:|:--------|
| 登录 + Auth复用 | ✅ | `pdd_login_v2.py` → `~/.pdd_auth.json` |
| 分类选择（SPP_searchItem） | ✅ | JS `dispatchEvent(MouseEvent)` |
| 标题填写 | ✅ | 标准 `fill()` |
| 主图/详情图上传 | ✅ | `set_input_files()` |
| 规格类型创建（AI按钮） | ✅ | 点击"AI添加规格"自动生成颜色+尺码 |
| 颜色值填入 | ✅ | `page.keyboard.type(val, delay=80)` + `Enter` |
| 尺码checkbox勾选 | ⚠️ | 隔离测试✅ 完整流程❌ → 半自动 |
| SKU表格（fill直填） | ✅ | IPT_input类，fill()直接可用 |
| 货号清除 | ⚠️ | 多层扫描，含 `#` 处理 |
| Submit | ⚠️ | 表单校验错误时卡住（需填写所有必填属性） |

## 🔑 关键突破：Playwright keyboard.type()

**这是React beast-core组件唯一接受的输入方式。**

```python
# ❌ 不行：fill / nativeSetter / dispatchEvent
inp.fill(val)                          # 值进DOM，React不认
page.evaluate('...dispatchEvent...')   # 同样

# ✅ 唯一可行
inp.click()
page.keyboard.type(val, delay=80)      # 逐字输入，Playwright驱动层模拟
page.keyboard.press("Enter")           # React捕获 → 生成tag
```

**原理**：`page.keyboard.type()` 在浏览器驱动层模拟真实键盘事件，React SyntheticEvent系统能捕获。JS `dispatchEvent` 创建的是"假"事件对象，React在production模式下会过滤。

## 规格区交互方法

### 颜色值（AutoComplete输入框）
```python
# 始终定位第一个输入框，每填完Enter后聚焦到下一个空行
inp = page.locator('input[placeholder*="选择或输入主色"]').first
inp.click()
page.keyboard.type("黑色", delay=80)
page.keyboard.press("Enter")
```

### 尺码checkbox（全选模式）
```python
# 点击第一个checkbox（"全选以下规格值"）一次性勾选所有尺码
# ❌ 不要用 scope selector（.package-item-container CBX_checkbox）
# ❌ 不要用 CBX_outerWrapper（wrapper无交互）
# ✅ 用全局 CBX_checkbox 第一个元素
page.locator('[class*="CBX_checkbox"]').first.click()
```

**CBX嵌套结构**（每个尺码5层）：
```
.package-item-container
  .CBX_outerWrapper      ← 外层容器
  .CBX_squareInputWrapper ← 输入包装
  .CBX_input              ← 隐藏的 <input type="checkbox">
  .CBX_square             ← 视觉方块
  .CBX_textWrapper        ← 文本标签
```

**只有 `[class*="CBX_checkbox"]` 是可点击的交互元素。**

### 隔离测试 vs 完整流程

- **隔离测试**（test_keyboard_spec.py）：1色 + 1全选 → SKU=11行 ✅
- **完整流程**（pdd_listing_v3.py）：4色 + 1全选 → SKU=0行 ❌
- **根因**：图片上传/标题填写后页面状态变化，全选checkbox在完整表单上下文中不触发React展开
- **唯一可靠方案**：半自动模式（headed浏览器，用户手动点规格值）

## 页面结构

### 发布流程
```
/goods/category → 搜索分类 → 选分类 → 确认
  → /goods/goods_add/index → 填表单 → 提交
```

### 分类选择
- 搜索框: `input[placeholder="请输入关键词搜索分类"]`
- 下拉项: `[class*="SPP_searchItem"]` (autoComplete dropdown)
- 确认按钮: `button:has-text("确认发布该类商品")`
- **关键**：Playwright `click()` 被 autoComplete dropdown 拦截
- **解决**：用 `page.evaluate()` 执行 JS `dispatchEvent(MouseEvent)`

### SKU 表格列序 (data-e2e-id="e2e-sku-table")
| 列 | 名称 | CSS |
|---:|:-----|:----|
| 1 | 库存 | `td:nth-child(1) input` |
| 2 | 拼单价(元) | `td:nth-child(2) input` |
| 3 | 单买价(元) | `td:nth-child(3) input` |
| 4 | 规格编码 | `td:nth-child(4) input` |
| 5 | 商品编码 | `td:nth-child(5) input` |
| 6 | 状态 | 非输入 |

**重要**：SKU表格输入框类名为 `IPT_input`（普通input），`fill()` 直接可用。不需要 nativeSetter hack。

### 商品参考价
- 位置: `#market_price input[placeholder="应大于商品最大单买价"]`
- fill() 可用 ✅

## Node.js v24 EPIPE — 缓解方案

**Playwright自带Node v24，系统nvm无效。**

```python
# 预防
args=["--disable-gpu", "--disable-background-networking"]
slow_mo=300  # 操作间隔

# 批量合并 — 将多次 query_selector+fill 合并为单次 page.evaluate
# 错误计数 — 同一错误>10次 → break 放弃等待
```

## 半自动断点流程

```
脚本自动完成                    用户手动操作
─────────────────────────────────────────────
登录 + Auth ✓
分类选择 ✓
标题填写 ✓  
主图上传 ✓
详情图上传 ✓
参考价填写 ✓
AI添加规格 ✓
颜色值填入(keyboard) ✓
                        → 🤚 用户在浏览器手动点尺码全选
                        → 确认SKU表格≥1行
                        → 终端按Enter继续
SKU价格填充 ✓
运费模板 ✓
提交发布 ✓
```

## 文件索引
- 发布脚本: `~/PDD/pdd_listing_v3.py` (~1600行)
- API客户端: `~/PDD/pdd_api_client.py`
- 表单探查: `~/PDD/inspect_form_live.py`
- 键盘测试: `~/PDD/test_keyboard_spec.py`
- AI规格测试: `~/PDD/test_ai_spec.py`
- PDD登录: `~/PDD/pdd_login_v2.py`
- Auth: `~/.pdd_auth.json`
- 上架数据: `~/PDD/商品/<日期>/<店铺名>/listing-ready/listing.json`

# React BeastCore 组件自动化交互指南

> 来源：拼多多商家后台 (mms.pinduoduo.com) 商品发布表单10轮实战验证，2026-05-03
> 适用范围：任何使用拼多多自研 BeastCore UI 组件库的 React SPA 自动化

## 核心认知

BeastCore 是拼多多自研的 React 组件库，用于商家后台。所有组件类名格式为 `{PREFIX}_{version}`（如 `IPT_input_5-188-0`），版本号随构建变化。

**关键原则：React production 模式下，只有真实浏览器事件能触发组件状态变更。JS 模拟的 synthetic 事件在 100% 的场景中失效。**

## 组件交互分级

### L0 — 普通 DOM input：fill() ✅
类名格式：`IPT_input_{version}`（标准 `<input type="text">`）
```python
page.locator('#market_price input').fill('99.9')  # ✅ 直接生效
page.locator('[data-e2e-id="e2e-sku-table"] input').fill('500')  # ✅
```

### L1 — AutoComplete 下拉（分类搜索）：JS dispatchEvent
搜索下拉项类名：`SPP_searchItem`（仅在下拉展开时存在于 DOM）
```python
# ❌ Playwright click() — 被 autoComplete dropdown 拦截
# ✅ JS MouseEvent dispatchEvent
page.evaluate('''() => {
    const items = document.querySelectorAll('[class*="SPP_searchItem"]');
    for (const item of items) {
        if (item.textContent.includes('女装')) {
            item.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            item.dispatchEvent(new MouseEvent('click', {bubbles: true}));
            return;
        }
    }
}''')
```

### L2 — AutoComplete 文本输入（颜色值）：keyboard.type() + Enter
```python
# ✅ 唯一有效方法：Playwright 原生键盘模拟
inp = page.locator('input[placeholder*="选择或输入主色"]').first
inp.click()
page.keyboard.type('酒红色', delay=80)   # delay 模拟逐字输入
page.keyboard.press('Enter')

# ❌ 无效：JS dispatchEvent(KeyboardEvent) — React 不认
# ❌ 无效：page.evaluate() 设值 + dispatchEvent
```

**注意**：此方法在简单表单（无大量前置操作）中有效，完整表单流程中可能因 DOM 状态变化而失效。详见 PDD 实战记录。

### L3 — CBX checkbox（尺码选择）
每个 checkbox 由 5 层嵌套组成：outerWrapper / squareInputWrapper / input / square / textWrapper。
```python
# ✅ 正确：点击 CBX_checkbox 组件
page.locator('[class*="CBX_checkbox"]').first.click(force=True)

# ❌ 错误：点击 CBX_outerWrapper 或其他子元素
page.locator('[class*="CBX_outerWrapper"]').click()
```

**全选技巧**：第一个 `CBX_checkbox` 是「全选以下规格值」。

### L4 — Radio Group（尺码标准切换）
```python
# 点击 radio label
page.locator('[class*="RDG_outerWrapper"]').filter(has_text='均码').click()
# 等待 3s+ 让 checkbox 重新渲染
page.wait_for_timeout(3000)
```

**坑**：切换 radio 可能重置已填的规格值，优先保持默认 radio 不做切换。

### L5 — beast-core Select 下拉框（2026-05-05 突破）
**重要性**: 关键组件 — PDD 商品发布中尺寸选择不再走 checkbox，而是 beast-core Select 下拉框。

类名: `ST_selectValueSingle_5-188-0` / `select_selectWrapper__36YSD`
识别: `data-testid=beast-core-select` (最精准)

```python
# 点击下拉触发器
page.locator('[data-testid="beast-core-select"]').click(force=True)
# 或通配符
page.locator('[class*="ST_head"]').first.click(force=True)

# 选择选项
page.get_by_text("默认模板").click(force=True)
time.sleep(2)
```

**关键特征**:
- 选项在点击触发后才渲染到 DOM → 可定位点击
- 输入框 `placeholder="未使用模板"` 可作为识别信号
- 下拉箭头: `ST_headDropdownArrow_5-188-0` + `ST_arrowIcon_5-188-0`
- 与运费模板下拉框相同组件体系
- **不需 fiber/CDP** — 走正常 React 交互流

## 选择器稳定性

BeastCore 类名含版本号后缀（`_5-188-0`），每次构建变化。**必须用通配符匹配**：

```python
# ❌ 硬编码：下次构建即失效
'.CBX_checkbox_5-188-0'

# ✅ 通配符：永远有效
'[class*="CBX_checkbox"]'
'[class*="IPT_input"]'
'[class*="SPP_searchItem"]'
```

## 诊断流程

遇到 beast-core 组件不响应时：

1. **全页截图** `page.screenshot(full_page=True)` → 确认组件实际渲染状态
2. **DOM 提取**：`page.evaluate()` 扫描目标区域所有元素（类名/文本/嵌套层级）
3. **隔离测试**：写最小复现脚本，跳过其他表单操作，只测试目标组件
4. **对比分析**：隔离测试成功 ≠ 完整流程可行，逐步骤加回操作定位破坏点

## PDD 实战发现 (2026-05-05 更新)

- SKU 表格输入框已从 beast-core `InputNumber` 降级为普通 `IPT_input`（2026-05 确认，fill() 有效）
- 「添加规格类型」和「AI添加规格」按钮并存 — AI 规格生成后尺码不是 checkbox，而是 Select 下拉框
- 尺码选择已突破：下拉选「默认模板」(M/L/XL/2XL/3XL/4XL) → 不需要 checkbox/fiber/CDP 攻击
- 表单校验错误「材质成分不能为空」表示类目有必填属性未填 — 需弹窗选择器方式
- 颜色 AutoComplete: keyboard.type() + Enter 唯一有效方法（2026-05 确认）
- 图片上传 Modal (MDL_modal) 加载后遮挡所有元素，Escape 无效，需 page.evaluate 隐藏

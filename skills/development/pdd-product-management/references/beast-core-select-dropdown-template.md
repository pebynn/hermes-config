# beast-core Select 下拉组件 — 尺码默认模板方案

> 日期: 2026-05-05
> 来源: PDD 商家后台 (mms.pinduoduo.com) goods_add/index 页面 DOM 分析
> 状态: 已替代 checkbox 攻击方案

## 背景

2026-05-05 前，尺码自动化一直尝试攻击 beast-core 的 CBX_checkbox 组件。2026-05-04 的 9 透镜研究确认 checkbox 根本不渲染 → 所有攻击手段无解。

发现：**颜色填充完成后，尺码位置渲染的不是 checkbox，而是 beast-core Select 下拉框。**

## beast-core Select 组件特征

| 属性 | 值 |
|------|----|
| 组件名 | beast-core Select |
| 类名模式 | `ST_selectValueSingle_5-188-0` (版本后缀随构建变) |
| 容器类 | `select_selectWrapper__36YSD` (hash后缀可能变) |
| 同体系参考 | 运费模板下拉框使用完全相同的组件 `select_selectWrapper` + `ST_selectValueSingle` |
| 可视化特征 | 点击后弹出下拉列表，选项可点 |

## 识别方法

```python
# 通过类名通配符匹配
page.locator('[class*="ST_select"]')
page.locator('[class*="select_selectWrapper"]')

# 通过位置筛选（在规格区域，y > 1000）
page.evaluate("el => el.getBoundingClientRect().y > 1000", select_element)
```

## 操作序列

```python
# 颜色已填完后的尺码自动化
# 1. 找下拉触发器（运费模板同款组件）
select_trigger = page.locator('[class*="ST_select"]').first
select_trigger.click(force=True)
time.sleep(1)

# 2. 等待下拉选项出现
# 选项类名: (可能含 "option", "select-option", "item" 等)

# 3. 点击"默认模板"
option = page.get_by_text("默认模板").first
option.click(force=True)
time.sleep(2)
```

## 为什么 Select 不需要 checkbox 的那些攻击？

| 特性 | Select 组件 | Checkbox 组件 |
|------|------------|--------------|
| DOM 渲染 | 选项在点击后才渲染到 DOM | AI 生成后 checkbox 根本不渲染 |
| 事件接收 | 正常 React 合成事件 | 生产模式屏蔽非合成事件 |
| 值同步 | 选中的文本直接映射到 state | DOM value ≠ React state |
| 自动化难度 | ⭐⭐（标准下拉交互） | ⭐⭐⭐⭐⭐（不可解封印） |

## 前提条件

下拉框只在下述条件成立时出现：
1. 颜色规格已创建完成（tag 已生成、保存到 state）
2. 尺码作为第二个规格类型等待配置
3. 页面没有 modal 遮挡

如果 dropdown 不出现，检查：
- 颜色 tag 是否已生成（`page.evaluate("document.querySelectorAll('[class*=\"tag\"]').length")`）
- Modal 是否已关闭（`style.display='none'`）
- 是否已滚动到尺码区域

## 延伸

此下拉框使用的是 `ST_selectValueSingle_5-188-0` — 与运费模板 Select 完全相同的组件体系。这意味着：
1. 任何 beast-core Select 都可用同类策略（click trigger → 选 option）
2. 下拉选项的渲染是真正的 DOM 元素，可被 Playwright 定位和点击
3. 不需要 fiber/CDP 等 hack

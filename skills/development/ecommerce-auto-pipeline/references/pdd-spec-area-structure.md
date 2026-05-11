# PDD 规格区域（stand_spec）DOM 结构与交互参考

> 基于 2026-05-03 实战探查 mms.pinduoduo.com 商品发布页，分类: 女装 > 毛衣/针织衫。
> **2026-05-03 更新**：表单加载后初始状态只有"AI添加规格"按钮，"添加规格类型"不可见。规格区需通过AI按钮触发。

## 初始状态（表单加载后）

规格区域初始为空 — **没有**颜色输入框、没有尺码checkbox、没有尺码radio、没有"添加规格类型"按钮。

仅有一个按钮：**"AI添加规格"**（`button:has-text("AI添加规格")`）。

点击后等 3-5 秒，应出现颜色输入框 + 尺码控件。这是当前唯一触发规格创建的方式。

## 整体 DOM 层级

```
#stand_spec (div.goods-sku-row.standard-spec)
  └── #newSpec (BeastCore Form Item — Grid layout)
      └── label: "商品规格"
      └── .goods-sku-box
          ├── 颜色分类 section
          │   ├── .property-name-title: "颜色分类"
          │   ├── .name-tips: "选择标准颜色可增加搜索/导购机会..."
          │   ├── .package-container.color (颜色值列表容器)
          │   │   └── .new-spec-single-color (每行一个颜色值)
          │   │       ├── input[placeholder="选择或输入主色"]   ← 颜色值输入
          │   │       ├── input[placeholder="备注（偏深/浅等）"] ← 备注
          │   │       └── button:has-text("本地上传")          ← 颜色图上传
          │   └── a:has-text("开始排序") (disabled when <2 colors)
          │
          └── 尺码 section
              └── .sizeStandardWrapper_sizeStandardWrapper__nC6eR
                  ├── .sizeStandardWrapper_title__7s9I-: "尺码"
                  ├── 尺码模板选择器 (BeastCore Select)
                  │   └── div[data-testid="beast-core-select"]
                  │       └── .ST_head_5-188-0 (触发器，tabindex=1)
                  │           └── input[readonly][placeholder="未使用模板"]
                  │           └── .ST_headDropdownArrow_5-188-0 (▼ 箭头)
                  ├── 尺码标准 RadioGroup
                  │   └── .RDG_outerWrapper_5-188-0
                  │       选项: 通用|中国码|欧码|英码|德码|美码|均码
                  │       当前选中: radio[checked] + .RD_active
                  ├── label:has-text("全选以下规格值") checkbox
                  └── 尺码值列表
                      └── .package-item-container × N
                          └── input-with-note
                              └── .normal-check
                                  └── .CBX_checkbox_5-188-0 (checkbox)
                                      ├── input[type="checkbox"] (隐藏)
                                      └── .check-wrapper (尺码文字)
```

## React SyntheticEvent 硬墙 ⚠️ (2026-05-03 终局验证)

4 种方法全测全败 — React Production build 不认任何模拟事件：
- `fill()` + `keyboard.press("Enter")` ❌
- `nativeSetter` + `dispatchEvent(InputEvent/KeyboardEvent)` ❌  
- `keyboard.type(val, delay=80)` + `press("Enter")` ❌
- 批量 `page.evaluate()` dispatchEvent ❌

**唯一可行：真人手动输入。半自动模式是唯一路径。**

## AI添加规格 vs 手动添加

**表单加载后规格区初始为空。** 旧版本有 `button:has-text("添加规格类型")`，当前版本只有 `button:has-text("AI添加规格")`。

点击AI按钮后：
- 自动生成颜色输入框（`input[placeholder*="主色"]`）
- 自动生成尺码选择器（checkbox + radio）
- 无需手动创建规格类型

## 关键 CSS 选择器

### 颜色分类

| 元素 | CSS 选择器 | 说明 |
|:----|:-----------|:-----|
| 颜色值输入 | `input[placeholder="选择或输入主色"]` | **自由文本输入，不是下拉选择器**。输入颜色名按 Enter 添加，是 AutoComplete 风格 |
| 颜色备注 | `input[placeholder="备注（偏深/浅等）"]` | 可选，描述色差 |
| 颜色图片上传 | `button:has-text("本地上传")` | 触发文件上传对话框 |
| 单行容器 | `.new-spec-single-color` | 每行包含一个颜色值输入 + 备注 + 上传按钮 |
| 颜色区容器 | `.package-container.color` | 所有颜色的列表容器 |
| 颜色预览图 | `.sku-preview-img` | SVG 图标/上传的图片缩略图 |

### 尺码分类

| 元素 | CSS 选择器 | 说明 |
|:----|:-----------|:-----|
| 尺码容器 | `.sizeStandardWrapper_sizeStandardWrapper__nC6eR` | 整个尺码 section |
| 模板选择器容器 | `div[data-testid="beast-core-select"]` 或 `.ST_outerWrapper_5-188-0` | BeastCore Select 组件 |
| **模板下拉触发器** | `.ST_head_5-188-0` | **点击此元素打开下拉**。有 tabindex=1 |
| 模板输入(readonly) | `input[placeholder="未使用模板"]` | 显示当前选中模板名，readonly |
| 下拉箭头 | `.ST_headDropdownArrow_5-188-0` | SVG 向下箭头图标 |
| 尺码标准 RadioGroup | `.RDG_outerWrapper_5-188-0` | 7个 tab: 通用/中国码/欧码/英码/德码/美码/均码 |
| Radio 选中态 | `.RD_active_5-188-0` | 当前选中的 radio tab |
| 单个尺码条目 | `.package-item-container` | 包含 checkbox + 尺码文字 |
| 尺码 checkbox | `.CBX_checkbox_5-188-0` | checkbox 组件，含隐藏的 `input[type="checkbox"]` |
| 尺码文本 | `.check-wrapper` | 直接子元素，显示如 "150/72A" |
| 全选 checkbox | `label:has-text("全选以下规格值")` | 全选所有可见尺码 |

### 通用规格操作

| 元素 | 选择器 | 说明 |
|:----|:-------|:-----|
| 添加规格类型 | `button:has-text("添加规格类型")` | 点击打开规格名输入弹窗 |
| 规格名输入 | `input[placeholder="请输入"]` | 弹窗中的规格名输入，按 Enter 确认 |
| 整体规格区域 | `#stand_spec` 或 `.goods-sku-row.standard-spec` | 规格区顶级容器 |
| 规格值 checkbox(通用) | `.CBX_checkbox_5-188-0` 或 `input[type="checkbox"]` | 选中/取消选规格值 |
| 提示文本 | `.sizeStandardWrapper_selectTip__1hBM6` | "可从尺码表模板选择尺码" |
| 全部尺码表按钮 | `a:has-text("全部尺码表")` | 打开完整尺码表弹窗 |

## 交互方法

### 设置颜色值（自由文本输入）

颜色输入是 **普通的文本输入框**，不是包含下拉选项的选择器：

```
1. 定位 input[placeholder="选择或输入主色"]
2. .fill("黑色") 或 .type("黑色")
3. page.keyboard.press("Enter")  → 添加为颜色标签
```

**不需要点击任何下拉箭头或选择选项** — 颜色值是直接键盘输入的。输入并回车后值会变成 tag 标签。

如需添加多个颜色值：每输入一个按 Enter，重复。

### 选择尺码模板（BeastCore Select 下拉）

```
1. 定位 .ST_head_5-188-0 (或 div[data-testid="beast-core-select"] 内的 header)
2. 点击该元素 → 下拉弹出
3. 点击下拉中的选项
```

点击触发器时，下拉菜单会展开（popper/portal 模式）。选项列表不在 DOM 中预渲染，点击后才动态生成。需要等待下拉出现后再选择选项。

### 勾选尺码值（复选框）

尺码值用 checkbox 勾选，不是输入：

```
1. 如果需要切换尺码标准，点击 RadioGroup 中的 tab
2. 勾选 .package-item-container 内的 .CBX_checkbox
3. 或用 Playwright: page.check('input[type="checkbox"]') 
```

### 添加规格类型（颜色/尺码规格头）

**2026-05-03 更新**：表单加载后规格区初始为空，**没有"添加规格类型"按钮**。唯一入口是 `button:has-text("AI添加规格")`。

```
1. 点击 button:has-text("AI添加规格")
2. AI 自动生成颜色+尺码框架（等 3-5 秒）
3. 检查生成结果：
   - colorInputs ≥ 1: 颜色框架生成 ✅
   - checkboxes 或 CBX_checkbox: 尺码checkbox出现 ⚠️ 初始可能为0，选radio后出现
4. 如果 AI 失败 → 页面可能动态出现"添加规格类型"按钮作为回退
```

> **注意**：AI生成的规格值框架受品类影响。毛衣/针织衫类目生成 15 个 checkbox（均码字母），时尚套装类目可能初始 0 个 checkbox，需选尺码标准 radio 后才出现。

## 关键发现

### 1. 颜色值 ≠ 下拉选择器

**颜色值是文本输入，不是下拉选择。** 不要试图找颜色下拉箭头或选项列表 — 不存在。它就是一个带 AutoComplete 功能的 `<input>`，用户直接输入颜色名称。

但页面中其它地方有很多 **ST 系列 Select 组件**（`ST_selectValueSingle_5-188-0` + `ST_headDropdownArrow_5-188-0` 箭头）:
- 品牌选择器 (`input[placeholder="请输入品牌名称搜索"]`)
- 多个属性选择器 (`input[placeholder="请选择"]`)
- 尺码模板选择器 (`input[placeholder="未使用模板"]`)

这些不要和规格值输入混淆。

### 2. 尺码模板下拉的触发方式

`div[data-testid="beast-core-select"]` 内的 `.ST_head_5-188-0` 是整个可点击区域（含 readonly input + 下拉箭头），点击任意部分触发下拉。不需要精确点击箭头图标。

### 3. 尺码默认值

当选择"通用"标准时，默认显示的尺码为：
150/72A, 150/76A, 155/80A, 160/84A, 165/88A, 170/92A, 170/96A, 175/100A, 175/104A, 180/108A, 180/112A

不需要全部勾选 — 只勾选需要的。

### 4. BeastCore UI 组件体系

PDD 商家后台使用自研 **BeastCore** UI 组件库：
- 输入框：`IPT_*` (IPT_outerWrapper, IPT_input, IPT_inputBlock...)
- 选择器：`ST_*` (ST_outerWrapper, ST_head, ST_selectValueSingle, ST_headDropdownArrow...)
- 按钮：`BTN_*` (BTN_outerWrapper, BTN_gray, BTN_textPrimary...)
- 复选框：`CBX_*` (CBX_checkbox, CBX_outerWrapper, CBX_input...)
- 单选框：`RD_*` / `RDG_*` (RD_outerWrapper, RDG_radioGroup...)
- 图标：`ICN_*` (ICN_outerWrapper, ICN_svgIcon...)
- 表格：`TB_*` (TB_td, TB_cellTextAlignLeft...)
- 网格布局：`Grid_*` (Grid_row, Grid_col...)
- 表单：`Form_*` (Form_item, Form_itemLabel, Form_itemContent...)
- Popover/Tooltip: `PP_*` / `PT_*` (PP_outerWrapper, PT_outerWrapper...)

类名后缀 `_{version_数字}`（如 `_5-188-0`）每次构建会变化，**不要硬编码完整类名**。用 `[class*="ST_selectValueSingle"]` 而不是 `.ST_selectValueSingle_5-188-0`。

# beast-core Select 下拉组件 DOM 结构

> 来源: 2026-05-05 PDD商家后台实战分析（F12 Inspect）
> 组件: 尺码模板选择器（sizeStandardWrapper_templateSelector）

## 完整 DOM 层级

```
sizeStandardWrapper_wrapperTitle__khwQT          ← 整体容器
├── sizeStandardWrapper_title__7s9I-             ← 标题行
│   └── <span>尺码</span>
└── sizeStandardWrapper_templateSelector__2Wf39  ← 选择器行
    ├── sizeStandardWrapper_left__3dw2A
    │   └── [data-testid="beast-core-select"]           ← Select 组件入口
    │       └── ST_outerWrapper_5-188-0 ST_medium_5-188-0  ← 外层
    │           └── [data-testid="beast-core-select-header"]
    │               └── ST_head_5-188-0              ← 可点击触发下拉
    │                   └── ST_selectValueSingle_5-188-0  ← 值显示区
    │                       └── ST_headInput_5-188-0
    │                           └── ST_inputBlock_5-188-0
    │                               └── input[data-testid="beast-core-select-htmlInput"]
    │                                   ├── placeholder="未使用模板"  ← 未选择时
    │                                   └── value="默认模板"          ← 已选择时
    ├── sizeStandardWrapper_selectTip__1hBM6
    │   └── "可从尺码表模板选择尺码"                    ← 提示文案
    └── 操作按钮
        ├── <a>编辑该模板</a>
        └── <a>全部尺码表</a>
```

## 关键 hook 点

| 目标 | 选择器 | 说明 |
|:-----|:------|:-----|
| 组件锚点 | `[data-testid="beast-core-select"]` | 最稳定的定位方式 |
| 外层容器 | `[class*="ST_outerWrapper"]` | 版本号可能变化，用通配符 |
| 触发头 | `[class*="ST_head"]` | 点击展开下拉菜单 |
| 值显示 | `[class*="ST_selectValueSingle"]` | 当前选中值展示 |
| 输入框 | `input[placeholder*="未使用模板"]` | 未配置时的 placeholder |
| 下拉面板 | `[class*="ST_optionPanel"]` | 展开后的选项面板 |
| 箭头图标 | `[class*="ST_arrowIcon"]` | 下拉箭头 SVG |

## 下拉菜单（展开后）

点击 ST_head 后，React 在页面 body 末尾渲染一个选项面板：

```html
<div class="ST_optionPanel_5-188-0">  <!-- 下拉面板 -->
  <div class="ST_option_5-188-0">默认模板</div>
  <div class="ST_option_5-188-0">...其他模板...</div>
</div>
```

## 常见问题

1. "值已存在但SKU表未扩展": 选中默认模板不等于尺码值已填入。需验证模板的尺码值（M/L/XL/2XL/3XL/4XL）是否已渲染为 SKU 行。
2. `text=默认模板` 匹配到隐藏元素: Playwright text locator 会匹配 DOM 中所有含此文本的元素，包括已选值的显示 tag。应先在 `ST_optionPanel` 内查找可点击选项。
3. 版本号后缀: beast-core 类名含 `_5-188-0` 等构建版本号，不同部署可能不同。必须用 `[class*="ST_xxx"]` 通配符匹配。

## 代码示例

```python
# 方法1: data-testid 定位（最可靠）
select = page.locator('[data-testid="beast-core-select"]').first
select.click(force=True)

# 方法2: 类名 + 位置过滤
for wrapper in page.locator('[class*="ST_outerWrapper"]').all():
    y = page.evaluate("el => el.getBoundingClientRect().y", wrapper)
    if 1100 < y < 2000:  # 规格区域 y 轴范围
        wrapper.locator('[class*="ST_head"]').first.click(force=True)
        break

# 方法3: placeholder 定位
page.locator('input[placeholder*="未使用模板"]').first.click(force=True)

# 选择选项：在下拉面板中找
current_val = page.evaluate("""
    () => document.querySelector('[data-testid="beast-core-select"] input')?.value || ''
""")
if current_val != '默认模板':
    # 在 ST_optionPanel 中遍历找"默认模板"并点击
    option = page.locator('[class*="ST_optionPanel"] [class*="ST_option"]')\
        .filter(has_text="默认模板").first
    option.click()
```

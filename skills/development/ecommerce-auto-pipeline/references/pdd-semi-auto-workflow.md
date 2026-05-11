# PDD 半自动发布工作流 (v3.1 更新)

## 背景

PDD 商品发布表单中的**规格值创建**（颜色 AutoComplete tag + 尺码 checkbox 勾选）需要通过 React SyntheticEvent 触发。经过 **6 轮浏览器探查 + 4 轮脚本跑测 (2026-05-03)**，确认：

- **SKU 表格输入框**已从 beast-core InputNumber 降级为普通 `IPT_input_5-188-0`，`fill()` 直接可用 ✅
- **市场参考价** `#market_price input` 的 `fill()` 也可用 ✅
- **AI添加规格按钮**可生成颜色+尺码框架 ✅
- **规格值填入**：4 种方法全部失败（fill/keyboard.type/nativeSetter/evaluate dispatchEvent），值进 DOM 但 React 不生成 tag ❌

### 四方法全测结果

| 方法 | 值进DOM | React生成tag | SKU表展开 |
|:-----|:------:|:----------:|:--------:|
| Playwright `fill()` + `keyboard.press("Enter")` | ✅ | ❌ | ❌ |
| JS `nativeSetter` + `dispatchEvent(InputEvent)` | ✅ | ❌ | ❌ |
| Playwright `keyboard.type(val, delay=80)` + `press("Enter")` | ✅ | ❌ | ❌ |
| 批量 `page.evaluate()` dispatchEvent(KeyboardEvent) | ✅ | ❌ | ❌ |
| **真人手动输入+回车** | ✅ | ✅ | ✅ |

**结论：React Production build 下，beast-core 受控组件只接受真实浏览器事件。唯一可靠路径是半自动模式。**

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
规格类型创建(颜色/尺码) ✓
                        → 🤚 断点：用户在浏览器中手动添加规格值
                           - 颜色: 点击 input[placeholder="选择或输入主色"]，输入颜色名，Enter
                           - 尺码: 选尺码标准 → 勾选 checkbox
                           - 确认 SKU 表格已生成多行
                        → 终端按 Enter 继续
SKU 价格填充 ✓
运费模板 ✓
货号清除 ✓
提交发布 ✓
```

## 当前实现

脚本：`~/PDD/pdd_listing_v3.py`（1413 行）

使用方式（headed 模式）：
```bash
cd ~/PDD
python3 pdd_listing_v3.py --date 2026-04-27 --single "贝黛娇服装源头-9407" --headless=0
```

## 已验证可用的自动化步骤

| 步骤 | 实现方式 | 状态 |
|:--|:--|:--|
| 分类选择 | JS `dispatchEvent(MouseEvent)` 绕过 autoComplete 拦截 | ✅ |
| 标题填写 | `fill()` | ✅ |
| 图片上传 | `set_input_files()` 直接传文件列表 | ✅ |
| 规格类型名 | `fill()` + `keyboard.press("Enter")` | ✅ |
| 颜色值输入 | `fill()` 到 `input[placeholder="选择或输入主色"]` | ⚠️ 值在框里但不转 tag |
| 尺码 checkbox | 选 RadioGroup 标准 + 勾选 `.CBX_checkbox` | ⚠️ 可勾选但表不生成行 |
| SKU 价格填充 | JS native value setter + dispatchEvent（绕过 inputNumber） | ✅ |
| 货号清除 | JS 全扫描清除含 `#` 的无效字段 | ✅ |
| 提交 | 4 层 fallback（click→evaluate→keyboard→JS dispatch） | ⚠️ Node v24 EPIPE |

## Node.js v24 EPIPE

Playwright 在 Node.js v24 下管道不稳定。缓解措施：
- Chromium 参数：`--disable-gpu --disable-setuid-sandbox --disable-extensions`
- `slow_mo=100` 操作间隔
- 提交时用 4 层 fallback

## 关联资源

- 规格区域完整 DOM：`references/pdd-spec-area-structure.md`
- SKU 表格列顺序：`references/pdd-sku-table-column-order.md`
- 主脚本：`~/PDD/pdd_listing_v3.py`

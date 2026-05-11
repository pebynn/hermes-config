# AI 规格生成 → 尺码 Checkbox 不渲染问题

> 日期: 2026-05-04
> 会话: pdd_listing_v3.py v3.2 → v3.3 攻坚

## 现象

点击「AI添加规格」后：
```json
{"generated": true, "colorInputs": 2, "checkboxes": 0}
```

颜色 input 框出现并能用 `keyboard.type()` 填充。但尺码 `.package-item-container .CBX_checkbox` **完全不存在于 DOM 中**，`checkboxes: 0`。

## 根因分析

AI 规格生成创建了尺码框架但**不会自动展开可交互的 checkbox**。两种可能：

1. **需先选尺码标准** — 点击"中国码" radio（`.RDG_outerWrapper` 中）后，checkbox 才渲染
2. **AI 生成走的是 input 模式**（新规格），不是 standard 模式（标准 checkbox）

## 草稿页面验证

用已有草稿 `goods_id=948677074377` 打开编辑页：
- 规格已配置完毕，SKU 表 6 行
- **页面上没有尺码 checkbox** — 因为草稿已完成选择，不需要再次渲染
- 仅有的 CBX_checkbox 元素是服务承诺勾选框（7天无理由/假一赔十），19 个

## v3.3 的 two-mode 检测逻辑

```python
spec_mode = page.evaluate("""() => {
    const checkboxes = document.querySelectorAll('.package-item-container .CBX_checkbox');
    const inputSizes = document.querySelectorAll('[class*="goods-spec-sku"] input[placeholder*="规格名称"]');
    if (checkboxes.length > 0) return 'standard';
    if (inputSizes.length > 0) return 'input';
    return 'unknown';  // ← AI 生成后经常走到这里
}""")
```

当前问题：AI 生成后两种模式都不匹配 → `unknown` → 无操作 → SKU 表只产生 1 行默认行。

## 下一步方向

1. **有头浏览器录制**：手动操作一次全新发布页面，记录 AI 生成后到 checkbox 出现的每一步 DOM 变化
2. **可能需要的步骤序列**：
   - AI 添加规格 → 等渲染 → 找尺码标准 radio（中国码/欧码/均码）→ 点击 → 等 checkbox 出现 → text-locator 点击
3. **备选**：完全跳过 AI 生成，手动分两步创建规格（颜色 + 尺码标准），确保 checkbox 必然出现

## 相关

- 主技能: pdd-product-management SKILL.md 第三节「规格值交互机制」
- 脚本: ~/PDD/pdd_listing_v3.py (v3.3)
- 草稿 URL: https://mms.pinduoduo.com/goods/goods_add/index?id=190754362113&goods_id=948677074377&type=edit
- EPIPE 问题: Node.js v24.13.0 的已知 bug，Playwright 管道断开

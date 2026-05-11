# Modal 干扰与手动创建规格 — 2026-05-04 发现

## PDD 图片上传 Modal 干扰

### 问题
页面加载后出现图片上传 Modal（`MDL_modal`），覆盖所有元素，阻止 Playwright 点击（包括 `force=True`）。

Modal 内容: "上传图片 图片空间上传 本地上传 AI智能做图"

### 修复（已验证可行）
```python
page.evaluate("""() => {
    document.querySelectorAll('[class*="MDL_modal"], [class*="MDL_container"]').forEach(m => {
        if (m.offsetParent !== null) m.style.display = 'none';
    });
}""")
page.wait_for_timeout(1000)
```

Escape 键不足以关闭该 Modal，必须用 `style.display='none'`。

## 手动创建规格类型（替代 AI 生成）

### 流程
```python
# 1. 关闭 Modal
page.evaluate("""() => { ... hide MDL_modal ... }""")

# 2. 点击"添加规格类型"
page.locator('button:has-text("添加规格类型")').click(force=True)
page.wait_for_timeout(3000)

# 3. 找空 input[placeholder="请输入"] 并聚焦
page.evaluate("""() => { ... focus empty input ... }""")
page.wait_for_timeout(500)

# 4. keyboard.type + Enter（fill 不被 React 接受）
page.keyboard.type("颜色", delay=80)
page.wait_for_timeout(500)
page.keyboard.press("Enter")
page.wait_for_timeout(6000)  # ← 等 React 更新 DOM
```

### 已验证（v4-v7）
- ✅ 第一次创建: (0/2)→(1/2) + 6行SKU
- ❌ 第二次创建: 填入后仍 (1/2)
- AI按钮: force click可行但 checkboxes:0

## 当前可达成
- Modal关闭 ✅ | 1规格类型 ✅ | 6行SKU ✅
- 2规格类型 ❌ | 尺码checkbox ❌

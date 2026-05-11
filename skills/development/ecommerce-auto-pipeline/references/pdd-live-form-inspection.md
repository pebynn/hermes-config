# PDD 表单现场探查方法论

> 2026-05-03 — 通过 Playwright headless + 已有 auth 直接导航到表单页，提取 DOM 结构和输入行为

## 为什么需要现场探查

PDD 商家后台是 React SPA，前端不定期更新。参考文档可能过时。每轮上架任务前应做一次快速探查（~30s）确认选择器和行为。

## 探查流程

### 1. 分类选择 → 进表单

```
搜索框输入关键词 → 等 SPP_searchItem 下拉 → JS dispatchEvent(MouseEvent) 点击匹配项 → 确认发布
```

**关键**：下拉项 class 是 `SPP_searchItem`，不是 `span.cate`。后者是分类树节点，不会触发 React 导航。

```python
page.type('input[placeholder="请输入关键词搜索分类"]', "女装", delay=50)
time.sleep(2)

clicked = page.evaluate("""() => {
    const items = document.querySelectorAll('[class*="SPP_searchItem"]');
    for (const item of items) {
        if (item.textContent.includes('女装') && !item.textContent.includes('中老年')) {
            item.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            item.dispatchEvent(new MouseEvent('click', {bubbles: true}));
            return item.textContent;
        }
    }
    return null;
}""")

confirm = page.locator('button', has_text="确认发布该类商品")
confirm.first.click(force=True)
```

### 2. 提取全部表单元素

用 JS evaluate 扫描所有可见 input/textarea/button/file-input/SKU表/规格区：

```python
fd = page.evaluate("""() => {
    const d = {inputs: [], sku: null, spec: null, btns: [], fileInps: []};
    document.querySelectorAll('input, textarea').forEach((el) => {
        const rect = el.getBoundingClientRect();
        const v = el.offsetParent !== null && rect.width > 1 && rect.height > 1;
        if (!v) return;
        
        let label = '';
        const fi = el.closest('[class*="Form_item"]');
        if (fi) { const l = fi.querySelector('[class*="Form_itemLabel"], label'); if (l) label = l.innerText.trim(); }
        
        d.inputs.push({
            ph: el.placeholder, type: el.type, id: el.id,
            cls: el.className?.substring(0,50), ro: el.readOnly,
            d2e: el.closest('[data-e2e-id]')?.getAttribute('data-e2e-id')||'',
            label,
        });
    });
    // ... SKU表、规格区、按钮、文件输入
    return d;
}""")
```

### 3. 按功能分类输入框

根据 placeholder/label/class 将 inputs 归为：标题/品牌/属性选择/参考价/SKU表格/运费/只读/其他。

### 4. 交互测试

对关键输入框分别测试 `fill()` 和 `nativeSetter+dispatchEvent` 两种填值方式，记录哪种生效。

```python
# fill()
el.fill("99.9"); time.sleep(0.2); v1 = el.input_value()

# nativeSetter
page.evaluate("""() => {
    const i = document.querySelector('selector');
    const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    s.call(i, '99.9');
    i.dispatchEvent(new Event('input', {bubbles: true}));
    i.dispatchEvent(new Event('change', {bubbles: true}));
}""")
time.sleep(0.2); v2 = el.input_value()
```

## 2026-05-03 探查结果摘要

| 发现 | 影响 |
|:-----|:-----|
| SKU表输入为 `IPT_input`，fill() ✅ | 废弃 nativeSetter hack |
| 市场参考价 `#market_price input` fill() ✅ | 简化价格填充 |
| 规格区初始无"添加规格类型"，只有"AI添加规格" | 优先走AI路径 |
| 13个"请选择"属性下拉，type=text | 需click触发BeastCore Select |
| SPP_searchItem 下拉选择有效 | 分类选择可用 |

## 探查脚本

`~/PDD/inspect_form_live.py` — 可独立运行的完整探查脚本，输出到 `~/PDD/form_live_analysis.json`。

# beast-core Checkbox React Fiber 攻击方案

> ⚠️ **v3.3 已降级为 fallback** — P0 方案已改为 17zwd text-locator 点击模式（Playwright text= locator + React 冒泡）。fiber 攻击法现在仅作为 text-locator 未生效时的第 1 级 fallback。
> 最新方案见 `pdd_listing_v3.py` (v3.3) 的 `_fiber_fallback()` 函数。
> 颜色输入的 tag 预填检测已添加（跳过已有颜色 tag 的输入步骤）。

> 适用: PDD 商家后台 / beast-core React SPA 生产模式
> 模块: ~/PDD/react_fiber_click.py (legacy)
> 状态: fallback only (v3.3+)

## 问题

beast-core (React 生产模式) 的 `.CBX_checkbox` 组件无法通过以下方式触发:
- `element.click()` / `element.click(force=True)` — Playwright
- `nativeSetter + dispatchEvent('input/change')` — 原生 DOM hack
- `dispatchEvent(new MouseEvent('click', ...))` — 模拟鼠标事件
- 键盘操作（Space/Enter）

React 生产模式禁用了 DevTools 相关的事件监听桥，只接受 React 合成事件系统内部的事件。

## 攻击路径

### 0. 前置扫描

```javascript
const cb = document.querySelector('.CBX_checkbox');
const reactKeys = Object.keys(cb)
    .filter(k => k.startsWith('__reactProps') || k.startsWith('__reactFiber'));
// reactKeys = ['__reactProps$xxxxxxxx', '__reactFiber$yyyyyyyy']
```

### 1. __reactProps（首选）

React DevTools 构建版本会在 DOM 节点上挂载 `__reactProps$<random_hash>` 属性:

```javascript
const propsKey = Object.keys(cb).find(k => k.startsWith('__reactProps'));
const props = cb[propsKey];

const handler = props.onClick || props.onChange;
handler({
    target: cb,
    currentTarget: cb,
    type: 'click',
    bubbles: true,
    cancelable: true,
    button: 0,
    buttons: 1,
    clientX: 0, clientY: 0,
    preventDefault: () => {},
    stopPropagation: () => {},
    persist: () => {},
});
```

**关键**: 合成事件对象必须包含 `preventDefault`/`stopPropagation`/`persist` 作为空函数。React 17/18 handler 会调用这些方法，缺少会导致 `Uncaught TypeError: e.preventDefault is not a function`。

### 2. __reactFiber → memoizedProps

如果 `__reactProps` 不存在（某些 React 构建），遍历 fiber 树:

```javascript
const fiberKey = Object.keys(cb).find(k => k.startsWith('__reactFiber'));
let fiber = cb[fiberKey];
let depth = 0;

while (fiber && depth < 25) {
    if (fiber.memoizedProps) {
        const handler = fiber.memoizedProps.onClick || fiber.memoizedProps.onChange;
        if (typeof handler === 'function') {
            handler({target: cb, currentTarget: cb, type: 'click', bubbles: true,
                     preventDefault: ()=>{}, stopPropagation: ()=>{}, persist: ()=>{}});
            break;
        }
    }
    fiber = fiber.return;  // 向上遍历
    depth++;
}
```

### 3. fiber.sibling

beast-core 某些组件（如 `PackageItem`）把交互 handler 放在兄弟 fiber 上:

```javascript
if (fiber.sibling && fiber.sibling.memoizedProps) {
    const sh = fiber.sibling.memoizedProps.onClick;
    if (typeof sh === 'function') {
        sh({target: cb, ...});
    }
}
```

### 4. fiber.memoizedState → hook.queue.dispatch

直接操作 React 内部状态（跳过 handler，直接调 dispatch）:

```javascript
let hook = fiber.memoizedState;
while (hook) {
    if (hook.queue && typeof hook.queue.dispatch === 'function') {
        const val = hook.memoizedState;
        if (typeof val === 'boolean') {
            hook.queue.dispatch(true);  // 直接设置选中状态
            break;
        }
        if (Array.isArray(val)) {
            // 可能是 selectedList，追加
            hook.queue.dispatch(prev => [...prev, newItem]);
            break;
        }
    }
    hook = hook.next;
}
```

### 5. CDP Input.dispatchMouseEvent

Playwright CDP 连接，发送 OS 级原生鼠标事件:

```python
cdp = page.context.new_cdp_session(page)

# 获取元素位置
pos = page.evaluate("""() => {
    const el = document.querySelector('.CBX_checkbox');
    const rect = el.getBoundingClientRect();
    return {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};
}""")

# 鼠标事件序列
cdp.send('Input.dispatchMouseEvent', {
    'type': 'mousePressed',
    'x': pos['x'], 'y': pos['y'],
    'button': 'left', 'buttons': 1, 'clickCount': 1,
})
cdp.send('Input.dispatchMouseEvent', {
    'type': 'mouseReleased',
    'x': pos['x'], 'y': pos['y'],
    'button': 'left', 'buttons': 0, 'clickCount': 1,
})
```

## 选中状态验证

beast-core checkbox 不会设置 DOM `checked` 属性。验证方式:

```javascript
const cb = document.querySelector('.CBX_checkbox');
const isChecked = cb.classList.contains('CBX_checked')
    || cb.classList.contains('checked')
    || cb.getAttribute('aria-checked') === 'true';
```

## 已知局限

1. `__reactProps` 依赖 React DevTools 构建。生产构建可能不存在，需回退 fiber walk。
2. `hook.queue.dispatch` 签名可能随 React 版本变化 — `dispatch(value)` vs `dispatch(prevFn)`。
3. CDP 方案依赖 `page.context.new_cdp_session()` — Playwright 必须启动 Chrome/Chromium（非 Firefox）。
4. 颜色选择（AutoComplete）**不需要** fiber 方案 — `keyboard.type()` + `Enter` 在 Playwright 中始终有效。

# PDD 材质成分填充策略

> 版本: v3.3 (2026-05-04)
> 实现: ~/PDD/pdd_listing_v3.py `_fill_material_composition()`

## 问题

PDD 女装类目要求填写"材质成分"字段。即使通过 DOM 操作成功写入值，React beast-core 组件也可能不识别变化，导致提交时仍报"材质成分不能为空"。

## 4策略递进方案

| 策略 | 方法 | 可靠性 |
|:--|:----|:------|
| 1 | 找含"材质成分"文本的父容器 → 找 input → `nativeInputValueSetter` 注入"涤纶100%" + dispatch input/change/blur | ⭐⭐⭐ |
| 2 | 点击"添加材质成分"按钮 → 弹窗中逐级匹配"涤纶"→"聚酯纤维"→"涤"→"聚酯" → 点击确认 | ⭐⭐⭐⭐ |
| 3 | 找 hidden input（by name/id关键词）→ 找 visible input → 找 contentEditable 元素 | ⭐⭐ |
| 4 | 点击材质成分区域 → keyboard.type("涤纶100%") + Enter | ⭐⭐⭐ |

## 2026-05-04 测试结果

```
策略1(直接填input): {'strategy': 1, 'success': True, 'method': 'nearby_input_fill'}
```

策略1成功填入了 DOM input，但 PDD 仍报"材质成分不能为空" — **这是 beast-core React 组件的通用问题：DOM 修改不等于 React state 更新。**

## 根因

beast-core 的 InputNumber/Select 组件使用 React 受控模式（value + onChange handler）。任何绕过 onChange 的 DOM 修改都不会同步到 React component state。提交时 PDD 读的是 React state 而非 DOM value。

## 对抗思路

同尺码 checkbox 的 fiber 攻击：
1. 找到材质成分 input 的 `__reactFiber$` 引用
2. 遍历找到 `memoizedProps.onChange`
3. 构造合成事件对象直接调用 onChange handler
4. React state 更新 → PDD 验证通过

或使用策略2（弹窗方式），因为弹窗中的交互走的是正常 React 事件流。

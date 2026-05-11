# PDD React 组件输入策略 — 完整方法论

> 基于 2026-05-03 6轮浏览器探查+4轮跑测
> 适用范围：任何使用 React Production build + beast-core 组件库的 SPA 表单自动化

## 总策略：分层递进

```
第一层：Playwright API — locator.fill(), keyboard.type(), locator.click()
         ↓ 如果 React 接受（普通 input 组件）
第二层：JS nativeSetter + dispatchEvent — 批量 page.evaluate() 减少 pipe
         ↓ 如果仍有 EPIPE 风险
第三层：半自动模式 — 人工介入规格值选择，脚本完成其余
```

## 组件类型策略映射

| 组件 | 类名标识 | 推荐策略 | 可靠性 |
|:-----|:--------|:--------|:-----|
| 普通 text input | `IPT_input_*` | `fill()` | ✅ 100% |
| beast-core InputNumber | `beast-core-inputNumber` | nativeSetter | ⚠️ PDD已降级为IPT |
| AutoComplete 颜色 | `input[placeholder*="主色"]` | `keyboard.type()` ⚠️ | 测试✅ 流程❌ |
| Checkbox 尺码 | `CBX_checkbox_*` | `locator.click()` ⚠️ | 测试✅ 流程❌ |
| RadioGroup | `RDG_outerWrapper label` | `locator.click()` ✅ | |
| Select 属性 | `input[placeholder="请选择"]` | 待验证 | |

## keyboard.type() 上下文依赖

测试脚本成功条件：品类=毛衣/针织衫, AI后15 checkbox可见, 填1色→Enter→tag生成→SKU=11行
完整表单失败条件：品类=时尚套装, AI后0 checkbox, 填4色✅但checkbox不触发React, SKU=0行

根因：React Production模式下 SyntheticEvent 需要特定 nativeEvent 引用，Playwright keyboard 产生的引用与真实事件不同。简单场景下事件池可复用接受，密集操作下耗尽拒绝。

## EPIPE 崩溃策略

slow_mo=300 → 批量evaluate减pipe → --disable-background-networking → 关键节点重启context → 错误计数10次break

推荐重启节点：图片上传后、规格填充后、提交前

# PDD 发布自动化 — 2026-05-04 根因突破

## 核心结论

**beast-core React 生产模式下，尺码 checkbox 在 DOM 中根本不渲染。** 这不是自动化"难度大"的问题，是工程原理级别的"不可能"——checkbox DOM 节点不存在，所有攻击手段 (fiber/CDP/text-locator/DOM hack/PyAutoGUI) 无的放矢。

## 当前 6 个阻塞点的根因诊断

| 阻塞 | 症状 | 根因 | 可解性 |
|------|------|------|:------:|
| AI规格后checkbox不渲染 | checkboxes:0 | AI生成走 input 模式，不创建 checkbox DOM | ❌ 不可解 |
| beast-core拒绝DOM注入 | fill()值不被React认 | 受控组件只认onChange handler | ❌ 不可解 |
| 第二个规格类型无法创建 | keyboard.type不被接受 | 同上+无稳定input定位 | ❌ 不可解 |
| 材质成分4策略全失败 | DOM改了但验证报错 | 受控组件读state不读DOM | ❌ 不可解 |
| Node v24 EPIPE | 管道崩溃 | v24.13.0已知bug | ✅ 降Node v18 |
| Modal干扰 | 弹窗覆盖元素 | 图片上传Modal | ✅ page.evaluate隐藏 |

## 三路径可行性

| 路径 | 全自动 | 可行性 | 关键门槛 |
|------|:-----:|:------:|---------|
| API pdd.goods.add | ⭐⭐⭐⭐⭐ | ⭐⭐ | ISV审核通过 |
| CSV批量导入 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 模板格式验证 |
| Playwright(浏览器) | ⭐⭐ | ⭐⭐⭐⭐⭐ | React封印不可解 |

## 战略建议

放弃"修复Playwright以征服beast-core"的思路。API + CSV 是数据→数据的直通通道。

1. **API 路径 (最佳)**: open.pinduodoo.com 注册"商家后台系统"应用 → 申请商品编辑权限 → 调 pdd.goods.add
2. **CSV 路径 (降级)**: 商家后台找批量导入模板 → 生成 Excel 文件 → 手动上传
3. **Playwright 路径 (兜底)**: 只做基本信息+图片+草稿，不碰规格区域

## 产出文件

全部研究产出: ~/research-skill-graph/projects/pdd-listing-full-automation-2026-05/
- executive-summary.md — 决策摘要
- deep-dive.md — 9透镜完整分析(25+来源)
- key-players.md — 系统/组织/API映射
- open-questions.md — 22个未解问题+P0/P1/P2路线图

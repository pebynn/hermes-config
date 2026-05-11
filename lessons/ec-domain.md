# EC-Domain Lessons — 电商管线教训

## 🔴 CRITICAL

### PDD 开放平台 API 对个人不可行
- ✅ **已升格** → `profiles/ec-domain/SOUL.md` 🔴硬约束段 (2026-05-07)
- **纠正次数**: 3
- ISV 企业审核是硬门槛，个人无法通过
- 不要再提"通过 API 上架"这条路径
- 标记为 DEAD END，后续不再讨论

## 🟠 HIGH

### PDD SKU 输入框降级方案
- SKU 输入框 React 组件：fill() 可用，但材质填充按钮 success=False
- React 不认模拟事件
- 尺码走 dropdown 选默认模板(M-4XL) 绕过 beast-core checkbox
- EPIPE crash (Node v24) 未解决

### 17网自动提取
- cs.17zwd.com 账号: 17825029430
- 4脚本: ~/.hermes/skills/development/ecommerce-auto-pipeline/scripts/
- 自动提取 price/title/SKU
- 上架三步: AI标题优化 + 定价(退货率25%) + SKU笛卡尔积

### 中老年女装选品限定
- 品类: 中老年女装/套装
- 爆款: 冰丝套装/碎花连衣裙
- 标题万能公式: 30汉字
- 定价: 1.3x/1.5x/1.8x (含退货率25%)
- 详情页: 六段式
- 差评: 2h 拦截
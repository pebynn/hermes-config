# PDD 商品发布 — 页面结构 & 自动化现状

> 检查日期: 2026-05-03
> 关联脚本: `scripts/pdd_listing.py`, `scripts/pdd_listing_publisher.py`
> 会话经验: 3个日期13款商品因脚本selector过期未能自动化发布

## 当前页面流 (React SPA, 2026-05-03 验证)

```
/goods/category                          ← 分类选择页（入口）
    ↓ 搜索分类 → 点击 → 确认
/goods/goods_add/index                   ← 商品信息填写页
    ↓ 填写标题/价格/SKU/图片/规格
    ↓ 点击"提交"或"预览"
发布成功页
```

### 分类选择页 (`/goods/category`)

```
结构: div.select-main-v2
    div.select-title → "选择分类"
    div.keywords-search → input[placeholder="请输入关键词搜索分类"]
    div.categories-grid → 大品类列表（服饰箱包/数码电器/...）
    button → "确认发布该类商品"
```

| 元素 | 选择器 | 
|:--|:--|
| 分类搜索框 | `input[placeholder="请输入关键词搜索分类"]` |
| 确认按钮 | `button:has-text("确认发布该类商品")` |
| 品类容器 | `.select-main-v2` |

**注意**: 输入分类关键词后，通过API异步加载搜索结果（不是静态列表）。需要 `wait_for_timeout` 等待下拉结果渲染。

### 商品信息填写页 (`/goods/goods_add/index`)

> ⚠️ 此页面的 selectors **未能在本次会话中验证通过**。`pdd_listing.py` 中的选择器全部基于旧版页面，已失效。

已知元素（需重新验证）：
- 标题输入框: placeholder 含 "请输入商品标题"（旧版）/ 可能已变更
- 主图上传: 非标准 `input[type="file"]`，而是 SPA 自定义上传组件
- 详情图上传: 同上。旧版尝试 `[class*="upload"]` 等通用选择器，均失效
- 规格/SKU 填写区域: 动态生成，依赖 React state
- 提交按钮: 文本含 "提交" 或 "预览"

## pdd_listing.py 失效原因

| 问题 | 旧假设 | 实际（2026-05） |
|:----|:-------|:---------------|
| 入口 URL | `/goods/add` | `/goods/category`（先选分类，后进表单） |
| `/goods/add` 行为 | 直接进入表单 | 302 重定向到 `/goods/goods_list` |
| 标题输入框 | `input[placeholder="请输入商品标题"]` | 分类未选时不存在，选分类后才能定位 |
| 主图上传 | `input[type="file"]` | 不存在标准 file input，SPA 自定义组件 |
| 详情图上传 | `[class*="upload"]` 点击触发 filechooser | 同上，全部失效 |
| 分类选择 | 自动选择器 `[class*="category"]` | 需先搜索关键词，再点搜索结果 |
| 提交 | `save_or_submit()` | 流程完全不一致，不可用 |

## 修复方向

### 方案A: 重写 pdd_listing.py

1. **Phase 1: 分类选择**
   - 导航到 `/goods/category`
   - 搜索分类关键词 + 点击结果 + 确认提交
   - 等待跳转到 `/goods/goods_add/index`

2. **Phase 2: 填写表单**
   - 重新发现所有输入框 placeholder / data-testid
   - 使用 Playwright `page.get_by_placeholder()` + `page.get_by_test_id()` 替代类名选择器
   - 图片上传: 使用 `page.locator('input[type="file"]')` (先找隐藏的 file input) 或 FileChooser 监听
   
3. **Phase 3: 提交**
   - 查找"提交"按钮并点击

### 方案B: 官方 API

- 拼多多开放平台提供商品发布 API
- 需企业资质审核（T+3工作日）
- 优点: 免浏览器、稳定、批量能力强
- 缺点: 门槛高、有调用频率限制

### 方案C: 半自动（浏览器指导用户操作）

- Playwright headed 打开浏览器
- 自动加载 listing.json
- 让用户手动填写+提交
- 循环处理多个商品时自动刷新页面

## 脚本索引

| 脚本 | 路径 | 状态 |
|:----|:----|:----|
| `pdd_listing.py` | `scripts/pdd_listing.py` | ❌ Python + Playwright，selector 过期 |
| `pdd_listing_publisher.py` | `scripts/pdd_listing_publisher.py` | ⚠️ 适配层，内调 pdd_listing.py，同样受影响 |
| `pdd_login_v2.py` | `~/PDD/pdd_login_v2.py` | ✅ 登录模块，可用（已验证 auth 有效） |

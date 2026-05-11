---
name: ecommerce-auto-pipeline
description: 电商一站式管线 — 中老年女装/套装方向，采集→搜索→下载→上架准备→PDD发布→运营管理全流程
version: 12.0.0
allowed-tools:
  - terminal
  - file
  - delegate_task(ec-domain)
arguments:
  - name: username
    description: 17网账号
    default: "17825029430"
  - name: max_products
    description: 最大下载商品数
    default: 8
  - name: date
    description: 上架数据日期 (YYYY-MM-DD)
    default: today
  - name: tier
    description: "定价策略: traffic(引流)/profit(利润)/image(形象)"
    default: profit
  - name: stage
    description: "管线阶段: all/sourcing/listing-only/ops"
    default: all
when-to-use: |
  用户说"帮我选品/选款/找货源"、"选品裙子/T恤/长裤"、"上架准备"、
  "做上架数据"、"出listing"、"标题优化"、"定价方案"、
  "一键上架"、"发布商品"、"订单管理"、"售后处理"、"运营看板"
hooks:
  pre-pipeline:
    - 确认品类方向是否为中老年女装/套装
    - 检查 17 网登录凭证是否有效
    - 发布阶段：检查 ~/.pdd_auth.json 是否存在（`python3 ~/PDD/pdd_login_v2.py --check`），不存在则需先 `--headed` 登录
    - 检查是否需加载 pipeline-bus skill 了解数据契约
  post-pipeline:
    - 输出 listing-ready/ 目录路径
    - 推荐重点款给用户确认
    - 如有订单导入，生成 PDD/运营/ 目录结构
history:
  v11.1.0: v3.3规格填充升级 — 17zwd text-locator点击模式(P0) + 尺码标准radio选择 + 材质成分四策略递进 + spec mode检测(standard/input)
  v11.0.0: keyboard.type()突破React墙 + CBX_checkbox全选模式 + EPIPE pipe合并策略 + 开放平台API(pdd.goods.add)双路径 + references/pdd-open-platform-api.md + references/pdd-listing-automation.md重写
  v10.0.0: 实战修正 — scrapling→原生Playwright + headed-first登录模式 + 滑块缺口匹配型确认
  v9.0.0: 新增 PDD 商家后台自动化（scrapling StealthySession + pdd_login.py）+ references/pdd-backend-automation.md + templates/pdd_login.py
  v6.0.0: 新增 orchestrator.py 三阶段总控 + pdd_listing_publisher.py 发布适配层 + pipeline-bus 数据契约 + 定价(1.3x/1.5x/1.8x, 退货率20%) + fulfillment骨架
  v5.2.0: 新增 Claude Code 风格 frontmatter（allowed-tools/arguments/when-to-use/hooks）
  v5.1.0: 均码/单尺码商品自动扩展为 L/XL/2XL/3XL/4XL/5XL 六码
  v5.0.0: SKU笛卡尔积生成; DeepSeek AI标题优化(从.env读key); 完整坑点文档
  v4.4.0: SKU(颜色/尺码)提取; DeepSeek AI标题优化
  v4.3.0: 下载时提取price+title写入_店铺信息.json
  v4.2.1: 移除死代码, pipeline检查退出码
author: Hermes Agent
tags: [ecommerce, automation, pdd, 17zwd, dropshipping, 中老年女装, listing-prep, ai-title, sku-extraction, pitfalls, orchestrator, fulfillment, pipeline-bus]
---

# 电商选品管线（中老年女装/套装方向）

## 适用场景

接收 research-domain 输出的选品关键词 → 到17网找对应款式 → 批量下载ZIP → 解压归档 → 上架准备（AI标题/定价/SKU生成/图片处理）。热词采集环节由 research-domain 域负责。

> **经营主体：中老年女装、套装。** 关键词、搜索、选品都围绕这个品类展开。

### 供应链路径选择（v8.0 新增）

当前管线默认走 **17网 → 下载 → 上架** 路径。随着月销量增长，应考虑升级供应链路径：

| 月销规模 | 推荐供应链路径 | 参考技能 |
|:--------|:-------------|:--------|
| <100件 | 17网一件代发（当前管线默认） | — |
| 100-300件 | 17网 + 1688 试单并行 | `pdd-c2m-supply-chain` |
| 300-500件 | 1688 直采为主，17网补充 | `pdd-c2m-supply-chain` |
| 500-1000件 | 1688 稳定合作 + 评估产业带直采 | `pdd-c2m-supply-chain` |
| 1000件+ | 产业带直采 + 评估拼工厂定制 | `pdd-c2m-supply-chain` |

> **月销300件是直采经济性临界点**。低于此量级，17网一件代发的综合价值（零库存风险/无需质检能力/无MOQ门槛）仍高于直采。详见 `pdd-c2m-supply-chain`。

---

## 管线概览

```bash
# ========== 一站式全流程（推荐） ==========
# 密码可通过 HERMES_ZW_PASSWORD 环境变量设置（推荐），或 --password 参数传入
python orchestrator.py --stage all --username 17825029430 --password 17825029430

# ========== 分阶段执行 ==========
# 只选品（采集→搜索→下载→上架准备）
python orchestrator.py --stage sourcing --max 8

# 只发布（消费已有 listing-ready/ 数据）
python orchestrator.py --stage listing-only --publish

# 只运营（订单/售后/库存/看板）
python orchestrator.py --stage ops

# ========== 传统单步 ==========
# 采集→搜索→下载
# 密码可通过 HERMES_ZW_PASSWORD 环境变量设置（推荐），或 --password 参数传入
python pipeline.py --username 你的17网账号 --password 密码

# 上架准备（图片/标题/定价/SKU）
python prepare_listing.py --date $(date +%F) --preview   # 预览
python prepare_listing.py --date $(date +%F)             # 正式

# PDD 自动上架 ⚠️ 脚本 selector 已过期，需修复后使用
python pdd_listing.py --date $(date +%F) --publish

# listing-ready → 发布适配（写入 publish_result.json）⚠️ 同上
python pdd_listing_publisher.py --date $(date +%F) --publish
```

### 管线数据流（pipeline-bus）

```
sourcing                             pdd                       fulfillment
采集→搜索→下载→prepare_listing  →  listing-ready/       →  订单/售后/库存/看板
                                    ┌─────────────────┐
                                    │ listing.json     │→ pdd_listing.py → 发布
                                    │ 定价方案.txt      │→ publish_result.json
                                    │ main_*.jpg       │
                                    │ detail_*.jpg     │
                                    └─────────────────┘
                                         Contract A               Contract B/C
                                    (pipeline-bus skill 定义)
```

> 所有跨域数据契约定义在 `pipeline-bus` skill 中。涉及跨域传数据时，先 `skill_view(name='pipeline-bus')` 检查字段格式。

---

## PDD 商家后台自动化（v10 — 2026-05 实战版）

**实际落地路径：原生 Playwright，非 scrapling。** scrapling 在 Node.js v24 下有 EPIPE 兼容性问题（详见下方坑点表）。最终方案：先 `--headed` 手动过一次滑块 → 保存 `~/.pdd_auth.json` → 后续全部 headless 复用。

```bash
# 首次登录（需要桌面环境，手动过滑块）
python3 ~/PDD/pdd_login_v2.py --headed

# 后续 headless 复用
python3 ~/PDD/pdd_login_v2.py              # 登录
python3 ~/PDD/pdd_login_v2.py --check      # 检查会话
python3 ~/PDD/pdd_login_v2.py --show       # 查看 auth 信息
```

**核心机制：**
- `playwright.sync_api` 原生 Chromium + 手动 stealth（JS 注入 `navigator.webdriver` 覆盖）
- 会话持久化：`context.storage_state()` → `~/.pdd_auth.json`
- headed 模式：出现滑块 → 提示用户 → 轮询等待登录成功（最长 5 分钟）
- 代码位置：`~/PDD/pdd_login_v2.py`
- 凭据：已硬编码（可环境变量覆盖）

> ⚠️ PDD 滑块是**缺口匹配型**，headless 自动求解 8+ 轮全败。不要在 headless 下指望自动过滑块。
> 完整记录 → `references/pdd-login-automation.md`

---

## 四阶段详解

### Phase 1：三平台关键词采集（`collect_hot_words.py`）—— 由 research-domain 域执行

> ⚠️ **职责边界**：热词采集是市场调研行为，归 research-domain 域。ec-domain 内部 sourcing 阶段不直接调用 collect_hot_words.py，而是接收 research-domain 输出的关键词列表。

纯 requests 实现，**不要用 Playwright 采词**——搜索页是重型SPA，不可行。

| 平台 | 接口 | 特点 |
|:----|:----|:----|
| 淘宝 | `suggest.taobao.com/sug` | 长尾词，适合递归展开 |
| 拼多多 | 首页HTML嵌入式JSON | 短品类词 |
| 抖音 | `aweme/v1/web/hot/search/list/` | 新闻热点，服装相关极少 |

#### 采集策略

- **种子词** = `中老年女装` + `中老年套装` + 品类词(裙子/T恤/衬衫/长裤/短袖/两件套/外套)
- 每个种子词→淘宝展开→拼多多展开 = 层层下发
- `--max` 参数一次性取够

```bash
# 只采集不搜索下载
python collect_hot_words.py --max 50
# 运行pipeline时内嵌采集
python pipeline.py --max 8
```

#### 品类筛选

- **定向采集** `--category 中老年女装` 或 `--category 中老年套装`
- 自动过滤：童装、大码女装（XXL以上）、孕妇装、运动服、内衣、婚纱
- 过滤规则：title 排除关键词识别

### Phase 2：17网搜索 & 下载（`search_and_download.py`）

> **Playwright 是关键依赖。** cs.17zwd.com 是 React SPA，requests/BS 完全不管用。

```bash
# 在 venv 中安装
pip install playwright
playwright install chromium
```

#### 搜索逻辑

| 场景 | 行为 |
|:----|:-----|
| 有采集词 | 按词依次搜索，词与结果无映射则用品类词兜底 |
| 无采集词 | 直接用 4 个固定品类词搜索 |

#### 下载流程

```python
page.goto("https://cs.17zwd.com/search?keyword=" + keyword)
page.wait_for_selector("div.s-result-list")
# 读取结果列表 -> 逐个进入商品详情页
page.goto(f"https://cs.17zwd.com/item/{item_id}")
# 提取 price, title, sku -> 写入 _店铺信息.json
# 点击"下载图片/视频" -> Ant Design 弹窗 -> 勾选子项 -> 立即下载
# 等打包完成 -> 下载按钮出现 -> page.expect_download() -> 拿到 ZIP
```

**下载成功后**：
- ZIP 解压到 `{下载目录}/{店铺名}-{商品ID}/`
- 删除 ZIP 源文件
- `_店铺信息.json` 写入价格、标题、SKU信息

**幂等保护**：每次下载前检查目标文件夹是否已存在，存在则跳过。

#### 关键参数

```bash
python search_and_download.py --username 17825029430 --password 17825029430 --max 8
python search_and_download.py --username 17825029430 --password 17825029430 --max 8 --keywords "妈妈夏装,中老年真丝上衣"
```

| 参数 | 作用 |
|:----|:-----|
| `--max` | 最大下载商品数（默认 8）。17网搜索每页20个 |
| `--keywords` | 自定义搜索关键词逗号分隔 |
| `--output` | 输出目录（默认 ~/PDD/商品/日期/） |

### Phase 3：上架准备（`prepare_listing.py`）

对下载好的每一款商品执行三步加工：

```
商品目录/
├── 原图.jpg              # Phase 2 下载的原图
├── _店铺信息.json         # Phase 2 提取的价格/标题/SKU
│
准备后输出 → listing-ready/
├── main_01~N.jpg         # 主图(去水印+重命名)
├── detail_01~N.jpg       # 详情图
├── listing.json           # 完整上架数据(含SKU列表)
└── 定价方案.txt           # 定价明细
```

#### ① AI 标题优化

调用 DeepSeek API 生成优化标题：

```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com")
```

- **规则**：中老年女装/套装 ≤ 60 字，凸显面料/版型/舒适/气质，不能有违禁词
- **降级**：关键词匹配词库，如果 API 调用失败
- API key 从 `~/.hermes/.env` 的 `DEEPSEEK_API_KEY` 读取，不硬编码

#### ② 定价方案（三层策略）

| 策略 | 倍率 | 退货率 | 推广费 | 平台扣点 | 适用价格带 |
|:----|:----|:------|:------|:--------|:----------|
| `traffic`（引流） | **1.3x** | 20% | 10% | 0.6% | ¥25~49 |
| `profit`（利润，默认） | **1.5x** | 20% | 10% | 0.6% | ¥50~99 |
| `image`（形象） | **1.8x** | 20% | 10% | 0.6% | ¥100~199 |

```bash
# 指定定价策略
python prepare_listing.py --date $(date +%F) --tier traffic
python prepare_listing.py --date $(date +%F) --tier profit    # 默认
python prepare_listing.py --date $(date +%F) --tier image
python orchestrator.py --stage all --tier profit
```

```python
# 计算公式
售价 = 硬成本 × 倍率 / (1 - 退货率 - 推广费率 - 平台扣点)
净利 = (售价 - 硬成本 - 售价×平台扣点 - 售价×推广费率) × (1 - 退货率)
```

> 当前定价（2026-04-29）：引流1.3x / 利润1.5x / 形象1.8x，退货率统一20%。

#### ③ SKU 生成

- 颜色 × 尺码 笛卡尔积
- 每 SKU 分配 1000 件库存
- **均码/单尺码商品自动扩展**为 `["L","XL","2XL","3XL","4XL","5XL"]` 六码
- 生成 `listing.json` 含完整 SKU 列表

#### ④ 图片处理

- 去水印：右下角邻域填充
- 统一 JPG 格式
- 重命名：`main_01~N.jpg` / `detail_01~N.jpg`

---

## 使用示例

```bash
# 1. 进入脚本目录
cd ~/.hermes/skills/development/ecommerce-auto-pipeline/scripts

# 2. 一站式全流程（推荐）
#    密码可通过 HERMES_ZW_PASSWORD 环境变量设置（推荐），或 --password 参数传入
python orchestrator.py --stage all --username 17825029430 --password 17825029430 --max 8

# 3. 分步：只选品 → 只发布 → 只看运营
python orchestrator.py --stage sourcing --max 8 --preview
python orchestrator.py --stage listing-only --publish
python orchestrator.py --stage ops

# 4. 传统单步（兼容旧流程）
#    密码可通过 HERMES_ZW_PASSWORD 环境变量设置（推荐），或 --password 参数传入
python pipeline.py --username 17825029430 --password 17825029430 --max 8
python prepare_listing.py --date $(date +%F) --preview
python prepare_listing.py --date $(date +%F)
python pdd_listing.py --date $(date +%F) --publish

# 5. 输出目录
# ~/PDD/商品/$(date +%F)/listing-ready/
# ~/PDD/商品/$(date +%F)/publish_result.json
# ~/PDD/运营/
```

---

## PDD 商家后台自动化（发布层核心）

**✅ 2026-05-03 v3.1: SKU 表格 fill() 直填已验证可用**（IPT_input 类普通 input，不再需要 nativeSetter hack）。AI添加规格按钮一键生成颜色+尺码。双路径提交（提交并上架/保存草稿）。四维提交前校验。详见 `references/pdd-listing-automation.md`。

### 当前正确的页面流（已验证 2026-05-03）

```
/goods/category            ← 先选分类（非旧入口 /goods/add）
    ↓ 搜索分类关键词
    ↓ 选择搜索结果
    ↓ 点击"确认发布该类商品"
/goods/goods_add/index     ← 实际商品信息填写页
```

**入口必须是 `/goods/category`**。`/goods/add` 现在会重定向到 `/goods/goods_list`。

| 当前已知可用选择器 | |
|:--|:--|
| 分类搜索框 | `input[placeholder="请输入关键词搜索分类"]` |
| 确认按钮 | `button:has-text("确认发布该类商品")` |
| 分类容器 | `.select-main-v2` |

> 商品信息填写页 selectors 已验证通过（2026-05-03）。SKU 表格列顺序、拼单价/单买价字段位置、商品参考价字段均已确认。详见 `references/pdd-sku-table-column-order.md`。
> **规格区域（stand_spec）完整DOM结构** 已验证。颜色为自由文本输入（非下拉），尺码为 BeastCore Select 模板选择器 + checkbox 勾选。详见 `references/pdd-spec-area-structure.md`。

拼多多商家后台（mms.pinduoduo.com）是 React 16 SPA，自动化发布有两种路径：

| 路径 | 门槛 | 能力 |
|:--|:--|:--|
| 开放平台 API | 企业资质+审核 | 完整API（client_id+client_secret+access_token） |
| **Playwright + Scrapling**（主力） | 零门槛，有商家账号即可 | 全部后台操作 |

### 推荐：Playwright + Scrapling 浏览器自动化

Scrapling 的 `StealthySession` 内置 Cookie 持久化、反指纹（hide_canvas / block_webrtc）、Cloudflare Turnstile 处理，直接覆盖 P0 需求。

```bash
pip install "scrapling[all]"
scrapling install
```

登录页结构：React 16 SPA，`#usernameId` / `#passwordId` 稳定可定位。默认扫码登录，需先切到账号密码 Tab。有滑块验证码。

自动化优先级：**P0 Cookie持久化+Stealth → P1 商品发布对接 listing.json → P2 订单处理 → P3 运营数据**

> 详细方案对比、API获取流程、Scrapling 配置示例 → `references/pdd-merchant-automation.md`
> 开放平台 API 凭证获取 → `references/pdd-api-credentials.md`

## 管线断点检查（"接下来做什么"标准流程）

当用户问"接下来做什么/下一步/现在到哪了"，执行以下检查链，15秒内出结果：

```bash
# 三步快速状态扫描
1. Auth 检查: ls ~/.pdd_auth.json → 有=✓ / 无=需先登录
2. 中间产物: ls ~/PDD/商品/*/ → 统计下载日期+款数
3. 输出检查: ls ~/PDD/商品/*/listing-ready/ → 有=可发布 / 无=需跑上架准备
```

**响应模板**（三段式）：
```
当前状态：✓已就绪 / ✗缺X步骤
管线缺口：[具体阶段名]
下一步：[P1/P2/P3] + 一行描述 + 所需前置条件
```

只问一个阻塞性确认（如定价策略），不问一连串问题。

### 阶段判定速查

| 当前状态 | 下一步 | 执行脚本 |
|:--------|:------|:---------|
| 无17网下载 | Phase 1-2 选品下载 | `pipeline.py` 或 `orchestrator.py --stage sourcing` |
| 有下载无 listing-ready | Phase 3 上架准备 | `prepare_listing.py` |
| 有 listing-ready 无发布 | Phase 4 PDD发布 | `pdd_listing_publisher.py --publish` |
| 已发布无运营 | 运营基础设施 | `ec-ops-daily` skill + cron |

---\n\n## 常见问题 & 坑点

| 问题 | 原因 | 解决 |
|:----|:----|:----|
|| 17网下不了载 | 没登录 / 登录过期 | 确认账号密码正确。密码可通过 `--password` 传入，或设置 `HERMES_ZW_PASSWORD` 环境变量（推荐） |
| 采集不到词 | 种子词太窄 | 用 `--category` 换品类词或加 `--max` |
| 图片去水印没效果 | 水印位置非右下角 | 检查图片分辨率，调整 `prepare_listing.py` 的填充区域 |
| 标题优化报错 | DeepSeek API key 没配置 | 检查 `~/.hermes/.env` 的 `DEEPSEEK_API_KEY` |
| 回测数据为空 | 股票停牌/刚上市 | 跳过该股票或换时间窗口 |
| Python argparse 崩溃 | 中文括号内含 % 字符 | 用 %% 逃逸 |
| `pdd_listing.py --publish` 所有商品全部报错 | PDD 商品发布页面结构已变更，旧选择器失效 | 导航到 `/goods/category` 选分类，进入表单后使用 `[data-e2e-id=\"e2e-sku-table\"]` 定位SKU表。列顺序: ①库存 ②拼单价 ③单买价 ④规格编码 ⑤商品编码 ⑥状态。详见 `references/pdd-sku-table-column-order.md` |
| ~~orchestrator.py PDD_LISTING_SCRIPT 过期路径~~ | ~~orchestrator.py L35 指向过期的 `pdd_listing.py`~~ | ✅ 已修复。当前 orchestrator.py 已正确引用 `pdd_listing_v3.py`。记录保留作为历史参考。 |
| **pipeline.py 硬编码绝对路径** | pipeline.py L27 使用 `/home/pebynn/PDD/商品` 硬编码路径，其他脚本都用 `os.path.expanduser("~/PDD/商品")` | **P1 应修复**：改为 `os.path.expanduser("~/PDD/商品")`。当前功能等价但将来home目录变更或容器化部署会断裂。脚本位置：`~/.hermes/skills/development/ecommerce-auto-pipeline/scripts/pipeline.py` |
| PDD 滑块 headless 全败 | 缺口匹配型，盲拖命中率 0 | 用 `--headed` 手动过一次，auth 后续复用 |
| PDD 登录页弹窗遮挡 | beast-core-modal 拦截点击 | 用 `query_selector.click()` 代替 `locator.click()`，或 `page.keyboard.press('Escape')` |
| PDD 分类下拉点击被拦截 | autoComplete dropdown 拦截 pointer events | 用 JS `dispatchEvent(new MouseEvent('click'))` 代替 Playwright click |
| PDD inputNumber 组件 fill() 无效 | React 自定义组件不响应原生 fill | **已废弃**。2026-05-03 现场探查确认 SKU 表格输入已改为 `IPT_input` 普通 input，`fill()` 直接可用。原生 setter hack 仅其他 beast-core 组件可能需要。 |
| Node.js v24/v20 Playwright EPIPE | 长时间会话管道断开（累计~3-5分钟触发）。**Node.js v20 降级无效，同样崩溃**。 | **多层缓解无效**: `slow_mo=300` + `--disable-background-networking` + 批量 `page.evaluate` 减少pipe往返 + 错误计数→10次break均失败。Playwright自带Node v24，系统nvm无效。崩溃节点：图片上传→颜色填值→等待循环。**当前方案**: 使用 `pdd_login_v2.py --headed` 模式手动过滑块一次 → 保存 `~/.pdd_auth.json` → 后续 headless 复用。自动滑块求解暂不可靠。**临时方案**: 关键节点后重启browser context（代码需实现）。**根本解决方案**: 放弃自动滑块，改为手动介入模式或使用PDD开放平台API（需企业审核）。 |
| PDD 货号格式报错 | 17网 out_goods_id 含 # | 三层扫描: ① 全局 input 扫描含 # 的短字段 ② label 定位扫描（含"货号"/"商品编码"/"编号"的 label 关联 input）③ contenteditable 元素扫描。见 `references/pdd-listing-automation.md` 货号字段清除章节 |
| PDD SKU 表格行数不对/规格值未填充 | React Production模式下SyntheticEvent不认任何模拟事件 | **v3.3 17zwd text-locator 模式**: 不再攻击 checkbox 的 JS 层，而是点击包含文本的父元素让 React 冒泡捕获。失败时自动回退 fiber/CDP。先检测规格模式(standard/input)再执行对应操作。详见 `references/pdd-listing-automation.md` 规格值填充章节 |
| PDD 颜色规格值找不到下拉选项 | 误以为颜色是 Select/下拉组件 | **颜色值是自由文本输入**（`input[placeholder="选择或输入主色"`]），不是下拉选择器。直接输入颜色名+Enter，不要找下拉箭头。见 `references/pdd-spec-area-structure.md` |
| React beast-core InputNumber fill()失效 → 已修复 | 旧版SKU表格使用自定义InputNumber组件 | **2026-05-03浏览器探查**: SKU表格输入框已降级为 `IPT_input` 普通input，`fill()`直接可用。market_price同样fill()可用。代码已简化70+行→30行。 |
| 材质成分不能为空 | beast-core 受控组件不接受 DOM 注入 | **v3.3 四策略递进**: ① nearby input `nativeInputValueSetter` ② 弹窗选择器匹配"涤纶"→确认 ③ hidden/visible input 扫描 ④ keyboard.type。策略1成功填DOM但React不认（同checkbox问题），首选策略2弹窗。详见 `pdd-product-management` skill |
| **⛔ beast-core checkbox 全部阻塞不可解 (2026-05-04 根因)** | 尺码 checkbox DOM 根本不渲染 — 所有6层攻击手段(fiber/CDP/text-locator/DOM hack/PyAutoGUI)全无效 | **战略转向**: 放弃Playwright解决checkbox。改走API(pdd.goods.add)或CSV批量导入。详见 `pdd-product-management` skill 第三节根因分析 + references/root-cause-deep-dive-2026-05-04.md |
| **CSV批量导入 (2026-05 新发现路径)** | 之前从未研究过 | 商家后台支持Excel/CSV模板批量发布。用Python生成模板文件+手动上传。可能是成本最低的全自动路径。验证步骤: 登录后台→找批量入口→下载模板→分析格式。详见 `pdd-product-management` skill 第八节 |

---

- **高可用** — `pdd-merchant-backend-automation` — PDD 商家后台浏览器自动化（登录/Stealth/滑块/会话持久化）⭐ 2026-05-01 新增
- **发布表单** — `pdd-listing-automation` — PDD 商品发布表单 DOM 结构/inputNumber 填值/EPIPE 缓解/坑点 ⭐ 2026-05-03 新增
- **React输入策略** — `pdd-react-input-strategies` — Playwright操作React beast-core组件的分层方法论（fill/keyboard/evaluate/半自动）⭐ 2026-05-03 新增
- **开放平台API** — `pdd-open-platform-api` — pdd.goods.add全参数文档 + 注册流程 + 签名算法⭐ 2026-05-03 新增

## 关联技能

- **pipeline-bus** — 跨域数据契约，ec-domain 内部 sourcing→listing→fulfillment 流转时加载
- **ec-domain** — 电商全链路域（内部三阶段：sourcing选品→listing上架→fulfillment运营）
- **pdd-c2m-supply-chain** — C2M/直采供应链（产业带地图/成本对比/质检体系/月销300件直采临界点）⭐ v8.0新增
- `profile-ec-sourcing-agent` — ec-domain 内部选品阶段子代理预设
- `profile-ec-pdd-agent` — ec-domain 内部上架阶段子代理预设
- `profile-ec-fulfillment-agent` — ec-domain 内部运营阶段子代理预设

## 审计记录

- `references/system-audit-2026-05-10.md` — 全链路审计（选品/上架/订单/退货/库存/活动/店群），含阻塞根因分析和自动化缺口清单

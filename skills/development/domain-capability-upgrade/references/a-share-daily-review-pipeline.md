# A股每日复盘管线 — 研究驱动域创建的完整案例

## 背景

从零创建 writing-domain，方向为 A股每日复盘写作。
数据采集→量化分析→AI写作→公众号草稿箱发布，全自动化。

## 阶段1: 研究驱动

### 原始需求
"深度调研一下想做一个微信公众号或者小红书的写手"

### 执行
1. task-clarify → domain=research, priority=P2
2. load deep-research skill → delegate research-domain
3. research-domain 执行9维度研究，产出4文件在 ~/research-skill-graph/projects/content-creation-automation/

### 关键研究结论影响域设计

| 研究结论 | 对域设计的影响 |
|----------|---------------|
| 发布层是瓶颈（微信API草稿箱限非认证号） | 强制人工审核，不接受100%自动化 |
| 小红书无官方内容API | 砍掉小红书支持，仅专注公众号 |
| 免费工具链成熟（壹伴/135/通义千问） | 全部工具选免费版 |
| AI内容需人工去AI味 | 内容生成环节加质量评分+去AI处理 |

## 阶段2: 域创建

### 域目录结构
```
~/.hermes/profiles/writing-domain/
├── SOUL.md                    # 核心定义
├── config.yaml                # 配置
├── README.md                  # 使用指南
├── start.sh                   # 就绪检查
└── skills/
    ├── a-share-data-collector/     # 数据采集
    ├── a-share-review-writer/      # 复盘写作
    └── a-share-publisher/          # 草稿发布
```

### 数据目录（与域名解耦）
```
~/writing-data/
├── raw/          # AKShare原始数据 (JSON)
├── drafts/       # AI生成复盘文章 (Markdown)
├── publish-logs/ # 草稿箱同步日志
└── analysis/     # 量化分析报告
```

## 阶段3: 用户反馈→域重定向

### 原始创建
- 域名: wechat-writing-domain
- 方向: 通用微信公众号内容创作（热点追踪→写作→发布）
- 包含: 通用热点追踪、通用内容生成、草稿箱发布

### 用户反馈
"wechat-writing-domain名称变更为writing-domain，微信公众号文章方向调整为A股每日复盘"

### 重定向操作清单

| # | 操作 | 变更内容 |
|:-:|:----|:---------|
| 1 | mv 域目录 | wechat-writing-domain → writing-domain |
| 2 | 更新主SOUL.md | wechat-writing-domain → writing-domain + 描述改 |
| 3 | 重写SOUL.md | A股复盘全流程取代通用写作 |
| 4 | 重写config.yaml | 数据采集配置取代热点追踪配置 |
| 5 | 重建技能 | 删除旧3技能 → 创建新3技能（数据采集/复盘写作/发布） |
| 6 | 更新README+start.sh | 反映A股复盘定位 |
| 7 | 数据目录迁移 | ~/wechat-writing-data → ~/writing-data |

### 关键决策点

**为什么要全重建而非局部修改**：
- 通用热点追踪 → A股数据采集：数据源完全不同（热榜→AKShare）
- 通用内容生成 → 复盘写作：模板完全不同（爆文→5节复盘）
- 旧技能名含"wechat-"前缀 → 新技能用"a-share-"前缀（能力导向命名）
- 旧数据目录含"wechat" → 新目录脱域名耦合（~/writing-data/）

### 踩坑记录

| 坑 | 现象 | 对策 |
|:---|:-----|:-----|
| 技能名含域名前缀 | wechat-topic-tracker → 域改名后技能名不匹配 | 能力导向命名，不去域名绑定 |
| 数据目录含域名 | ~/wechat-writing-data → 域改名后路径需迁移 | 固定路径，与域名解耦 |
| API凭证绑定域配置 | 微信/AI API不受域名影响 | config.yaml中API配置不变 |

## 产出管线详情

### 1. 数据采集（15:30-16:00）

```python
# AKShare 数据管线
import akshare as ak

# 指数
sh = ak.stock_zh_index_daily(symbol="sh000001")
sz = ak.stock_zh_index_daily(symbol="sz399001")
cy = ak.stock_zh_index_daily(symbol="sz399006")

# 北向资金
north_flow = ak.stock_hsgt_north_net_flow_in_em()

# 行业资金流向
sector_flow = ak.stock_sector_fund_flow_rank(
    indicator="今日", sector_type="行业资金流向"
)

# 涨停股
limit_up = ak.stock_zt_pool_em(date="YYYYMMDD")
```

### 2. 量化分析（16:00-16:30）

复用现有 ~/quant/ 资产：

```bash
# 全A信号日报
python3 ~/quant/daily_signal_report.py --output-format json

# 因子信号（待确认路径）
# python3 ~/quant/signal_engine.py --date YYYY-MM-DD
```

计算指标：
- 涨跌家数比：`up_count / down_count`
- 量比：`today_volume / avg_5day_volume`
- 北向态度：>50亿"大幅流入"、>10亿"小幅流入"、< -50亿"大幅流出"

### 3. AI复盘写作（16:30-17:00）

调用 Qwen3 / DeepSeek，严格遵循5章节模板：

```markdown
# 【每日复盘】YYYY-MM-DD A股收盘总结

## 一、大盘回顾
## 二、资金风向标
## 三、热点解读
## 四、技术看盘
## 五、明日策略

*风险提示：AI辅助创作，不构成投资建议*
```

约束：
- 严禁个股推荐（仅板块级点评）
- 不含未来涨跌预测
- 必须包含风险提示
- 字数1000-2000

### 4. 发布到草稿箱（17:00-17:30）

微信公众号API：
```
POST /cgi-bin/draft/add?access_token=TOKEN
{
  "articles": [{
    "title": "【每日复盘】2026-05-05 A股收盘总结",
    "author": "复盘点金",
    "content": "<h2>HTML正文</h2>",
    "need_open_comment": 1,
    "is_aigc": 1
  }]
}
```

**Token管理**：
- 缓存到 ~/.hermes/credentials/wechat_access_token.json
- 有效期7200秒，过期自动刷新
- 首次需手动获取

### 5. 人工审核（次日开盘前）

用户登录 mp.weixin.qq.com → 草稿箱 → 审核 → 发布

推荐发布时间：次日上午9:00-9:30（开盘前黄金时段）

## 完整时间线

| 时间 | 环节 | 自动化 | 人工 |
|:---:|:-----|:------:|:----:|
| 15:00 | A股收盘 | — | — |
| 15:30 | AKShare数据采集 | ✅ | — |
| 16:00 | 量化分析+计算指标 | ✅ | — |
| 16:30 | AI生成复盘文章 | ✅ | — |
| 17:00 | 同步微信草稿箱 | ✅（API） | — |
| 次日9:00 | 审核发布 | — | ✅ |

## 调用命令

完整流程：
```
使用 writing-domain 域生成今日A股复盘
```

分步执行：
```
采集今日A股数据
写今日A股复盘
发布今日复盘到草稿箱
```

## 阶段4: C级全量升级（2026-05-05）

在基础管线（数据采集→AI写作→草稿箱）之上，进行全量升级：

### 新增能力

| 能力 | 脚本 | 状态 |
|:--|:--|:--|
| 4张分析图表生成 | generate_charts.py | ✅ |
| 图表嵌入复盘文章 | generate_review.py v2 | ✅ |
| 微信素材库图片上传 | publish_draft.py v2 | ✅ |
| 周末周总结+热点识别 | weekly_summary.py | ✅ |
| 封面图生成（cron兜底） | publish_draft.py matplotlib fallback | ✅ |
| 跌停数据修复 | collect_data.py v3 | ✅ |
| .env统一加载（cron兼容） | 5脚本统一模式 | ✅ |
| 微信IP白名单检测 | publish_draft.py --check-ip | ✅ |
| 安全硬化 | config.yaml → 环境变量 | ✅ |

### 最终脚本架构（5脚本）

```
skills/
├── a-share-data-collector/scripts/collect_data.py       # 数据采集
├── a-share-review-writer/scripts/
│   ├── generate_charts.py    # 4张图表（K线/热力/资金/宽度）
│   ├── generate_review.py    # AI复盘写作+图表嵌入
│   └── weekly_summary.py     # 周总结+热点识别
└── a-share-publisher/scripts/publish_draft.py           # 发布+图片上传
```

### 图表管线

mplfinance + matplotlib 4张图表，全部使用中文字体 WenQuanYi Zen Hei：

| 图表 | 工具 | 数据源 |
|:--|:--|:--|
| kline.png | mplfinance 蜡烛图+MA5/10/20 | akshare.stock_zh_index_daily_em |
| sector_heatmap.png | matplotlib 横向柱状 | all_data.json 板块数据 |
| capital_flow.png | matplotlib 双轴柱状+累计线 | akshare.stock_hsgt_hist_em |
| market_breadth.png | matplotlib 直方图+阈值线 | akshare.stock_zh_a_spot_em |

### 升级中踩坑

| 坑 | 现象 | 解决 |
|:--|:--|:--|
| 中文缺字 | matplotlib用DejaVu Sans，汉字全部方框 | 检测 WenQuanYi Zen Hei → rcParams设置 → rm font cache重建 |
| mplfinance字体 | mpf.plot() 不认rcParams | 每个图表函数内重新 plt.rcParams.update() |
| AKShare列名变更 | `净流入`→`当日成交净买额` | 查实际columns后修正 |
| cron环境无env | DEEPSEEK_API_KEY未设置 | 5脚本统一加.env文件解析兜底 |
| 微信AppSecret暴露 | config.yaml明文 | 移至.env，config用 ${WECHAT_APP_SECRET} |
| 跌停数据为空 | type参数不支持 | 改用 stock_zt_pool_dtgc_em() |
| image_generate在cron不可用 | Hermes工具链依赖 | matplotlib自动生成封面图兜底 |
| 旧SOUL.md过期 | 无图表/新脚本引用 | 重写核心职责+工具链+工作流+产出+子代理表 |

### 安全硬化清单

- config.yaml: 3个密钥 → `${ENV_VAR}` 引用
- validate_wechat_api.py: 硬编码fallback → 清空
- .env: 新增 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`
- 所有脚本: 自动从 `~/.hermes/.env` 加载环境变量

### 验证结果

`start.sh` 运行通过：✅ 5脚本 + 4依赖 + env检测全部通过。
全管线端到端：数据采集 ✅ → 图表4/4 ✅ → AI生成 ⚠️（API超时，降级报告可用）。

## 相关文件路径

- 域目录：~/.hermes/profiles/writing-domain/
- 数据：~/writing-data/{raw,charts,drafts,publish-logs}/
- 主SOUL.md注册：~/.hermes/SOUL.md → "可调度资源"表
- 验证报告：~/writing-data/verification_report.md

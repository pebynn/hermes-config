# Global Lessons — 全域通用教训

> 每一条都是被纠正 ≥1 次的真实错误。跨域复用，避免各域独立发现同一教训。

## 🔴 CRITICAL

### DeepSeek API 间歇性抖动
- **模式**: ~20% 失败率，API 连接超时/401
- **修复**: 自动切换到智谱 glm-4.5-air (open.bigmodel.cn)
- **触发**: circuit-guard 5次/30min → 自动熔断
- **日期**: 2026-05-07 确认

### 跨厂商 fallback 必须不同 provider
- **反例**: deepseek-v4-pro → deepseek-v4-flash (同 provider，无效)
- **正例**: deepseek-v4-pro → 智谱 glm-4.5-air
- **原因**: provider 自己宕机时，同 provider fallback 零保护

### 数据铁律：所有数字必须来自 API 原始返回值
- **跨域适用**: writing-domain、finance-domain
- **禁止**: 自行计算涨跌幅/成交额/换手率/涨跌家数或任何衍生数据
- **原因**: 复权/除息/停牌导致自行计算完全错误
- **事故**: writing-domain 捏造涨跌家数 2772→真3513; finance-domain 列映射错致全盘数据错

### API 映射铁律：字段索引不能靠猜
- **跨域适用**: 所有调用外部API的域
- **Sina**: parts[1]=今开, parts[2]=昨收, parts[3]=收盘, parts[4]=最高, parts[5]=最低, parts[9]=成交额
- **东财**: f43=最新价, f170=涨跌幅×100
- **MySQL列坑**: amount=成交额, turnover=换手率 (不是成交额列名叫turnover)
- **原则**: 映射错误 = 全部数据错误 = 不可原谅。先验证1条再批量

### 子代理长任务必须用 cron，禁止 delegate
- **跨域适用**: 所有域
- **原因**: delegate_task 随父会话取消而终止。cron 独立生命周期
- **触发**: 任何预计 >2min 的任务


### 用户给的架构思路必须落地为脚本/SOUL.md/MCP工具，不能只存 memory
- 用户提出'每日 agenda 自动继承未完成任务+计时'的思路后我听到了但没做，直到被指出才动手。模式识别：用户给的架构设计/工程思路不是闲聊信息，必须立即评估可行性并落地为操作路径（新脚本/SOUL.md规则/MCP工具）。做完才归档。纠正次数: 2+
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### 模式级纠正必须立即写为 lessons，不当下次推断
- 用户给出的不是'修这个bug'，而是'处理这类问题的方法论'。触发信号：用户说'你是不是应该举一反三'/'这就是同一个模式'/'我说的是这个意思吗'。正确做法：(1)立即保存为lesson含触发条件 (2)扫描当前所有系统中有没有同类问题 (3)一次性处理完所有同类。反例：只修复当前点，下次同样问题变个形式又来。纠正次数: 1
- **纠正次数**: 1
- **首次发现**: 2026-05-09

### cron 诊断：last_run_at=null ≠ 故障
- 新创建的 cron 首次检查时 last_run_at=null 不代表 cron 损坏
- 判断标准：到了预定时间但未执行 = 故障。尚未到达首次执行时间 = 正常
- 诊断流程：先查 cron 的创建时间和调度时间 → 再判断状态
- 反例：error-learner 和 lesson-promoter cron 刚创建，尚未到达 22:00/周一03:00 → 错误诊断为"从未运行"需要修复
- **来源**: 20260507_200432_bd67b0

### 路径/目录变更必须立即固化到 memory + 更新 old references
- 用户纠正路径后必须(1)立即写 memory (2)检查 lessons 中是否有旧路径引用并更新
- 反例：brain 目录从 ~/tools/data-sync/brain/ 迁移到 ~/brain/ 后，系统仍继续使用旧路径，触发"说了多少次：不要再写错的"严厉纠正
- **正解**: 登录新目录路径后立即 memory add，并在 global.md 或对应域 lessons 中添加记录
- **来源**: 20260507_200432_bd67b0

## 🟠 HIGH

### 晚间 API 黑窗模式（跨域共性）
- **东财 push2**: 19:00-08:00 不可用 → Sina 备源
- **DeepSeek API**: 间歇性抖动 → 智谱 fallback
- **通用策略**: 每个数据源配至少一个不同供应商的备源，含自动降级+30s超时

### 多源交叉验证铁律
- **跨域适用**: writing-domain(3-way)、finance-domain(3-way)
- **单源不可信**: 任何时候必须 2+ 源交叉验证
- **发现不一致**: 先加源验证，不要直接信任任一源

### 渲染/可视化产出必须实际运行验证
- **跨域适用**: writing-domain(图表)、code-domain(前端/画图)
- **禁止**: 仅代码检查就报"已验证"
- **要求**: 跑真实流程，看实际产出物

### 子代理产出后主代理必须验证
- 子代理 summary 是 SELF-REPORT，不可信
- 文件写入/HTTP POST 后 → 主代理必须 stat/read/curl 确认
- 跨域适用: 所有域

### 双脚本同步铁律
- **跨域适用**: writing-domain 的 generate_review↔weekly_summary, code-domain 的多模块
- 改A必须检查B是否受影响（数据源/结构/格式/API）

**纯文本约束不可靠 — 关键规则已脚本化：**
- `enforce_delegate.py` — delegate前强制 lesson_inject + 死路检查 + 铁律注入
- `cost-circuit-breaker.py` — 日成本>$15.00自动暂停高消费cron
- `rule_audit.py` — 每日10:00扫描违规用语/死路提及
- `data_guard.py` — 数据铁律强制门禁

### 用户不需要学任何命令
- **来源域**: code-domain
- **跨域适用**: 所有域
- **禁止**: 向用户推送 shell 命令语法、curl 示例、python 调用方式
- **正例**: 内部调度完成，只汇报结果。用户只关心"做了什么"和"结果是什么"
- **纠正次数**: 1

### 新建cron前必须检查调度冲突
- **来源域**: ops-domain
- **跨域适用**: writing-domain、ops-domain（所有新建cron的域）
- **要求**: 新建cron前先 `cronjob action=list` 检查已有时间分布。同一分钟冲突→错开≥5min；同一±30min已有3+ cron→评估合并或分散；同功能重复cron→合并或删除其一；可合并推送的任务→评估合并为一个prompt
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### 研究/分析类任务必须走 deep-research 协议
- **来源域**: research-domain
- **跨域适用**: research-domain（热词/竞品调研）、finance-domain（策略/标的深度研究）、writing-domain（科普/深度分析）
- **原则**: 任何标为"研究/分析/调研/评估"的任务，必须完整走 deep-research 协议（多源采集→交叉验证→结构化输出）
- **禁止**: 用 web_search 搜索两下就出结论 — 这不是研究，是偷懒
- **反例**: 用户要求调研"公众号AI内容识别策略" → 之前仅 web_search → 后来 deep-research 才发现关键信息（平台能识别AI生成内容并降权）
- **纠正次数**: 1
- **首次发现**: 2026-05-08

## 🟡 MEDIUM

### Z.ai 从中国不可达
- api.z.ai 从中国服务器超时
- 用 open.bigmodel.cn 替代（同一 GLM_API_KEY）

| 先验证再集成
- **跨域适用**: finance-domain(策略IC验证)、code-domain(新工具验证)
- 任何新信号/新工具/新数据源 → 先独立验证 → 确认有效 → 再集成到管线

### 脚本产出必须验证语法
- **来源域**: code-domain
- **跨域适用**: writing-domain、finance-domain、ops-domain（所有产出 .py 的域）
- **要求**: 每次产出 .py 脚本后立即: `python3 -c "import py_compile; py_compile.compile('script.py', doraise=True)"`
- **常见 bug**: async with 缩进错误导致 context 提前关闭
- **首次发现**: 2026-05-07

### 使用 `skills_list` 工具而非 `ls ~/.hermes/skills`
- `ls` 在某些目录结构（未挂载设备）下会卡死
- 内置 `skills_list` 工具稳定可靠
- **纠正次数**: 1
- **来源**: 20260429_183418_9a881f

### 部分读取的文件不可直接覆写
- 文件以 offset/limit 分页读取后（部分视图），不可直接用 write_file 覆写
- 必须先完整读取文件全文，再决定编辑策略
- **来源**: 20260429_183418_9a881f

### 简单编辑跳过 todo 直接 patch
- 用户偏好：路径清晰时直接使用 `patch`，无需 `todo` 中间规划步骤
- 适用：已知具体内容的替换/添加
- **纠正次数**: 1
- **来源**: 20260429_183418_9a881f

### 子代理超时不等于失败
- delegate_task 超时后，文件/安装可能已部分完成
- 超时后应先检查实际状态（文件是否存在、进程是否运行），再决定重试策略
- **来源**: 20260501_034251_246d02

### /tmp 数据被 reboot 清空
- **来源域**: ops-domain
- **跨域适用**: 所有域
- **反例**: self-evolution 工具在 /tmp/ 存储 → reboot 后全部丢失
- **正例**: 持久数据必须存储在 ~/ 下；每次运行前检查依赖 + 必要时自动重新初始化
- **首次发现**: 2026-05-07

### pip install 被禁止 → 用 uv tool install
- **来源域**: ops-domain
- **跨域适用**: 所有域（含 code-domain、writing-domain、finance-domain 等）
- **原因**: 系统限制 `externally-managed-environment`，`pip install` 被禁止
- **正例**: 直接用 `uv tool install <package>`（uv 在 ~/.local/bin/uv）；安装后通过 `head -1 $(which <tool>)` 获取正确 Python 解释器路径
- **纠正次数**: 1
- **首次发现**: 2026-04-30

### Playwright 浏览器依赖必须预装
- **来源域**: ops-domain
- **跨域适用**: writing-domain（雪球发布）、ec-domain（PDD上架）
- **反例**: 安装 playwright Python 包后直接使用 → 报错"浏览器二进制文件未找到"
- **正例**: 首次部署/环境初始化时手动执行 `playwright install chromium`；在 cron 初始化脚本中添加此步骤
- **首次发现**: 2026-05-08

---

## 👤 用户偏好（从 profile_observe 写入）

### 工作模式
- **活跃时间**: 凌晨1-4AM → 东财API可能不可用，各源需备选
- **主业**: 拼多多中老年女装电商，A股量化是副业
- **技术栈**: Ubuntu/zsh，熟悉 Hermes 高级配置，精通 A 股量化
- **语言**: 中英双语

### 沟通风格
- 指令级精简：只说"测试"二字就期望直接跑，不解释不铺垫
- 厌恶不确定词：禁止"可能/也许/大概/应该"，要么准确要么不说
- 只看结果：不回顾历史、不解释过程、不道歉保证
- 打断信号："停止"、"别找了"立即中止，不追问

### 价值取向
- "系统在变好"是核心工作价值
- 效率敏感：操作耗时过长会接管（"我自己来吧"）
- 架构一致性：纯调度不执行，MCP > skill，结构性方案 > 文本规则
- 成本敏感：主动要求从 reasoner 降级 flash

## 🗑️ 已确认死路（不再提及或尝试）

### PDD 开放平台 API
- **原因**: 需要 ISV 企业审核，个人不可行
- **替代**: 17 网选品 + Playwright 上架
- **警告**: 再提触发"一直说废话"严厉批评

### 雪球全自动发布
- **原因**: Playwright 被 React 前端拦截 + WAF防护
- **替代**: 降级为本地备份 + 手动发布指引

### V4 资金流生命周期策略
- **原因**: 核心资金流数据无法用于回测（北向2024-08停更，主力API频繁断连）
- **状态**: 用户已要求删除所有相关文件

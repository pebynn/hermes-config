# Ops-Domain Lessons — 运维教训

## 🔴 CRITICAL

### API Token 过期→全部cron级联失败
- 2026-05-08 17:21 CST: Hermes gateway API token 过期，所有 cron 作业级联失败
- 影响: graphify-daily / circuit-guard-hourly / 每日K线更新 / A股每日复盘生成+发布
- 共计 24+ 次 401 错误，跨 5+ 会话，全部下游作业停摆，无自动恢复机制
- **纠正次数**: 1
- **首次发现**: 2026-05-08
- 对策:
  1. 监控: cron 定期 curl 测试 token 有效性
  2. 告警: token 过期前 7 天发通知
  3. 自动刷新: 如果支持 refresh_token 则自动续期
  4. 所有 cron 出口必经 circuit-guard 熔断检测: 401 3次/5min → 暂停全部任务并通知


### 发现问题必须现场修复，不等着用户来问
- 排查到的问题分L1/L2/L3。L1直接修不汇报问题本身，只汇报修了什么。L2修完简报。L3暂停请示但必须先做完诊断给出选项。任何时候都不要列出一堆问题却不碰它们——用户要的是被修好的系统，不是问题清单。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### data_guard守门员: 所有管线脚本必须经过门禁
- data_guard.py (~/writing-data/shared/data_guard.py)已集成到collect_data/generate_charts/generate_review/weekly_summary/publish_draft共5个管线脚本。门禁含: 字段映射统一源(6种数据源)、采集交叉验证(值域+自洽性)、图表文件实体检查、标题格式审查、audit_guard四维审计(合规/数据/AI味/格式)、函数漂移检测。BLOCK级阻断管线，WARN级警告。每日06:00 drift检测cron。不经过data_guard的数据不准往下游走。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### pipeline_runner 是写作管线唯一入口，禁止直接运行脚本
- 所有写作管线操作必须通过 ~/.hermes/scripts/pipeline_runner.py 执行。支持6个动作: collect/charts/review/publish/weekly/gate。直接 python3 collect_data.py 等绕过方式跳过 data_guard 门禁。cron 已全部迁移到 pipeline_runner。任何修改/调试管线脚本的操作也必须通过 runner，不可直接执行脚本。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### 直接修，修不了再推QQ决策
- 问题修复规则: 任何系统问题(L1/L2)发现后直接动手修，不汇报过程不列问题清单。包含:cron噪音推送/MCP异常/管道死循环等可自愈的系统健康问题。只有修不了的(需要你决策/涉及不可逆操作)才推到QQ等你决策。不要等你说'修一下'才动手。纠正次数:1。首次发现:2026-05-09
- **纠正次数**: 1
- **首次发现**: 2026-05-09

### GLM API token 过期导致全系统级联故障
- **模式**: GLM API 令牌过期（Error 401 — 令牌已过期或验证不正确）导致:(1)title_generator 标题生成失败 (2)session_summarizer 会话摘要失败 (3)所有 cron job 失败(每日K线更新/A股复盘/复盘发布/circuit-guard/graphify) (4)活跃 session LLM 调用失败。**检测**: 检查 errors.log 中 '401' + '令牌已过期'。**修复**: 更新 API key/token 后需重启 gateway。**预防**: 设置 token 过期预警（提前7天检查）；token 轮换后自动验证所有 cron job 可用性。
- **纠正次数**: 1
- **首次发现**: 2026-05-09
## 🟠 HIGH

### 微信 cron 铁律
- weixin 推送错开 ≥1h
- 同分钟最多 1 条
- 多任务合并为一条消息
- 非紧急用 local
- 新建 cron 先列出现有 weixin 时间表避让

### /tmp 目录被 reboot 清空
- self-evolution 工具在 /tmp/ → reboot 后丢失
- 解决方案: 每次运行前检查 + 自动 clone
- 或迁移到 ~/.hermes/tools/


### Browser CDP 端口 9377 不可用
- Chromium DevTools 端口 9377 连接拒绝 (Connection refused)
- 需确保 Chromium 以 --remote-debugging-port=9377 启动
- 检测命令: curl -s http://localhost:9377/json/version
- 修复: chromium --remote-debugging-port=9377 --headless --no-sandbox
- **纠正次数**: 1
- **首次发现**: 2026-05-07

### Weixin iLink API 硬限流
- iLink sendmessage 返回 ret=-2 errmsg=rate limited
- 即使 cron 错开也可能触发 API 级硬限流
- 触发后需退避 ≥60s (当前默认 3s 不够)
- 同一用户连续 5 次失败 → 标记冷却 5min
- 来源: 2026-05-07 18:01-19:06 密集限流 → cron 消息丢失
- **纠正次数**: 1
- **首次发现**: 2026-05-07


### AKShare 大规模超时 → 信任 Sina 降级
- AKShare(index_us_stock_sina/futures_foreign_hist/stock_hk_index_daily_sina/stock_news_em/tool_trade_date_hist_sina) 频繁超时挂死。修复方案：1) 所有 AKShare 调用包裹 _timeout_call()，15s 超时自动跳过；2) Sina hq.sinajs.cn 作为可靠降级源，延迟<200ms；3) 交易日历超时则信任硬编码节假日+周末判断。morning_brief.py 已验证此方案可行。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### 创建cron前必须检查已有调度冲突
- 新建cron前必须先用 cronjob action=list 检查已有作业的时间分布。\n\n检查原则：\n1. 精确冲突：同一分钟有多个cron → 错开至少5分钟\n2. 30分钟窗口：同一时段(±30min)内如果已有3个以上cron → 评估是否可合并或分散\n3. 重复审核：同一行文已有相同功能的cron → 不重复创建（如circuit-guard-hourly和hourly-circuit-check）\n4. 可合并推送：同域任务时间相近 → 评估是否可以合并成一个prompt一次性完成\n\n操作决策：\n- 冲突 → 错开时间(至少差5min)\n- 同功能重复 → 合并或删除其一（优先保留no-agent脚本，便宜）\n- 同一管道顺序依赖 → 按依赖顺序排列时间（如15:30→16:00→16:30）
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### akshare tool_trade_date_hist_sina 挂死
- akshare.tool_trade_date_hist_sina() 的 sina 源经常永久挂死不返回，不能直接调用。需用 multiprocessing Process + timeout 包装（15秒超时）。已修复 margin_data.py 的 is_trading_day() 函数。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### akshare query.sse.com.cn IPv6 挂死
- query.sse.com.cn 的 IPv6 连接在 Python urllib3 中永久挂死（curl 能 fallback 到 IPv4）。解决方案：在 akshare API 调用前执行 _force_ipv4()，将 urllib3 的 allowed_gai_family 强制设为 socket.AF_INET。已修复 margin_data.py 的 fetch_margin_daily()。
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### QQBot WebSocket 快速重连循环
- 2026-05-08 20:37-21:37 CST: QQBot WebSocket 进入快速重连循环:\n- 06:00-20:30 正常间歇性断连 (约1次/5-30min)\n- 20:37 后恶化: 每 ~62s 一次 "WebSocket error: WebSocket closed"\n- 1小时内 77 次重连失败\n- 与 gateway 进程生命周期/API token 过期可能有关联\n对策:\n1. 连续 3 次重连失败 → 指数退避 (30s→60s→120s→300s max)\n2. 连续 10 次重连失败 → 停止 QQBot 适配器并通知\n3. 与 circuit-guard 联动: QQBot 失败计入熔断计数器\n4. 检查是否与 gateway API token 过期相关 (token → WebSocket auth → 被踢)
- **纠正次数**: 1
- **首次发现**: 2026-05-08

### Hindsight API 版本过旧导致批量记忆保留失败
- 触发: Hindsight retain failed: HindsightEmbedded 无 aretain_batch/aretain 方法。根因: Hindsight API 版本 < 0.5.0 时回退到 per-process document_id 模式，且 Embedded 客户端缺少 aretain_batch 方法。今日出现 30 次。修复: 升级 Hindsight 到 0.5.0+，验证 aretain_batch 可用。如无法升级则检查替代方案。
- **纠正次数**: 1
- **首次发现**: 2026-05-10
## 🟡 MEDIUM

### auto_prune 必须开启
- sessions/ 累积 1156 文件/494MB
- 开启 auto_prune + 7d retention → 降至 363MB
- 每天约 66 个新 session

### gbrain sync 每 6h
- cron 47600ff91a8f
- Bun 路径: ~/.bun/bin/bun

### pip install 失败 → 用 uv tool install
- 系统限制 `externally-managed-environment`，`pip install` 被禁止
- 应直接用 `uv tool install <package>`（uv 在 ~/.local/bin/uv）
- 安装后通过 `head -1 $(which <tool>)` 获取正确 Python 解释器路径
- **纠正次数**: 1
- **来源**: 20260430_153543_8eb96a

### GBrain embed 僵尸进程处理
- `gbrain embed --stale` 可能挂死，阻塞 PGLite 数据库
- 检查命令: `ps aux | grep gbrain`
- 修复: `kill <PID>` 后重试
- **来源**: 20260501_034251_246d02

### graphify Python 路径初始化
- `uv tool install graphifyy` 后，graphify 需要知道正确的 Python 解释器
- 手动写入: `echo $(head -1 $(which graphify)) > graphify-out/.graphify_python`
- 否则报错: `graphify-out/.graphify_python: 没有那个文件或目录`
- **来源**: 20260430_153543_8eb96a

### WeChat 发布 API errcode 50002 处理
- `errcode: 50002` / `"user limited"` 表示当日配额耗尽或账号限频
- 三级降级（API→Cookie→Browser自动化）全部可能失败
- 应实现自动退避重试: 首次失败后等 5min 重试，最多 3 次
- 不要立即重试 — 限频有固定时间窗口
- **来源**: 20260506_104750_8ed504

### 雪球cookie验证：HTTP 200 + 有效name字段 = PASS
- verify_cookie() 判定标准：收到 HTTP 200 + 返回体含有效 name 字段 → 视为通过
- 雪球API可能返回市场数据（如"上证指数"）而非用户信息 — 这是正常响应
- **反例**: 期望用户信息格式 → 误判cookie无效 → 导致时间浪费
- **修复**: 改为检查 HTTP 200 + 含name字段 + 返回体非空
- **来源**: 20260507_032807_dd37de

### Gateway 未配置用户白名单
- Gateway 启动时 GATEWAY_ALLOW_ALL_USERS 未设置
- 需在 ~/.hermes/.env 中设置 GATEWAY_ALLOW_ALL_USERS=true
- 或配置各平台白名单 (TELEGRAM_ALLOWED_USERS/QQBOT_ALLOWED_USERS 等)
- 未授权用户会不断重连，产生噪音日志
- **纠正次数**: 1
- **首次发现**: 2026-05-07

### Playwright浏览器依赖需预装
- 雪球发布脚本依赖Playwright的chromium浏览器，但浏览器二进制文件未随pip install自动安装。需手动执行 'playwright install chromium' 来下载chromium浏览器，否则浏览器自动化会失败并降级为本地备份。建议在cron环境初始化或首次部署时预先安装。今日已开始安装，后续cron将可用。
- **纠正次数**: 1
- **首次发现**: 2026-05-08
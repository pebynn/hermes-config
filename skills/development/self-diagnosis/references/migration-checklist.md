# Hermes 全量迁移检查清单

新机器完整打包迁移后必做的检查项。按修复顺序排列。

## 1. 系统基础

```bash
# 磁盘、内存、uptime
df -h / && free -h && uptime -s

# Hermes 目录结构完整性
ls ~/.hermes/profiles/          # 应看到 6 个域
find ~/.hermes/skills -name 'SKILL.md' | wc -l  # 应 >= 150
ls ~/.hermes/mcp-servers/       # 12 个 MCP server 脚本
ls ~/.hermes/cron/jobs.json     # 必须存在
ls ~/.hermes/.env               # 必须存在
ls ~/.hermes/SOUL.md            # 必须存在
```

## 2. API Key 替换（迁移后必须）

迁移后原机器的 API key 大概率已失效。需逐项验证：

```bash
# DeepSeek
curl -s --max-time 10 https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'

# TAVILY
python3 -c "from tavily import TavilyClient; TavilyClient(api_key='$TAVILY_API_KEY').search('test')"

# GLM (fallback)
curl -s https://open.bigmodel.cn/api/paas/v4/models \
  -H "Authorization: Bearer $GLM_API_KEY"
```

## 3. Venv 完整性（⚠️ 高频陷阱）

打包后的 venv 可能缺依赖、缺 pip binary：

```bash
# pip 可能不存在，用 python3 -m pip 替代
~/.hermes/hermes-agent/venv/bin/python3 -m pip --version

# 关键依赖检查
~/.hermes/hermes-agent/venv/bin/python3 -c "import tavily; print('OK')" 2>&1
~/.hermes/hermes-agent/venv/bin/python3 -c "import pymysql; print('OK')" 2>&1

# 修复：用 python3 -m pip（不是 pip）
~/.hermes/hermes-agent/venv/bin/python3 -m pip install tavily-python pymysql \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**陷阱**：`~/.hermes/hermes-agent/venv/bin/pip` 可能不存在，
必须用 `python3 -m pip`。这是 venv 目录直接拷贝的常见副作用。

## 4. Systemd 环境变量（🔴 必做）

MCP 子进程从 gateway 继承环境变量。systemd service 不配置的话，
所有 MCP server（web_search/deep_research/graphify）都会缺 key。

### 4.1 添加 EnvironmentFile

```ini
# ~/.config/systemd/user/hermes-gateway.service
[Service]
EnvironmentFile=-/home/pebynn/.hermes/.env
Environment="TAVILY_API_KEY=tvly-dev-..."
Environment="DEEPSEEK_API_KEY=sk-..."
Environment="GLM_API_KEY=..."
Environment="MYSQL_STOCK_PASSWORD=stock123"
```

**为什么需要 EnvironmentFile + 显式 Environment 双保险**：
- `EnvironmentFile` 从 .env 文件读取（格式：KEY=VALUE，一行一个）
- 显式 `Environment=` 用于系统关键 key，即使 .env 文件损坏也能保底
- 前面的 `-` 表示文件不存在时不报错

### 4.2 添加 env_passthrough

```yaml
# ~/.hermes/config.yaml
terminal:
  env_passthrough: [TAVILY_API_KEY, DEEPSEEK_API_KEY, GLM_API_KEY, MYSQL_STOCK_PASSWORD]
```

这样 terminal 子进程也能继承这些变量。

### 4.3 重启验证

```bash
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service

# 验证 env 已注入
GATEWAY_PID=$(systemctl --user show hermes-gateway.service -p MainPID | cut -d= -f2)
cat /proc/$GATEWAY_PID/environ | tr '\0' '\n' | grep TAVILY
```

## 5. Gateway 重启陷阱

重启可能卡在 `deactivating` 状态 60-90 秒（等待 MCP 子进程优雅退出）。
有 QQ Bot 连接时尤其慢。

```bash
# 如果卡超过 90 秒，强制 kill
systemctl --user kill -s SIGKILL hermes-gateway.service
systemctl --user reset-failed hermes-gateway.service
systemctl --user start hermes-gateway.service
```

## 6. MySQL 数据迁移

Schema 迁移了，但数据不会自动迁移：

```bash
# 检查
mysql -u stock -pstock123 stock_kline -e "SELECT COUNT(*) FROM kline;"

# 如果为 0，需要回填历史 K线
# 约 5000 只 A 股 × 多年数据 = 1-2 小时
```

## 7. Sessions 和 Checkpoints 清理

打包时带了旧会话和快照，新机器上无意义：

```bash
# 删除 cron 会话（瞬时垃圾）
find ~/.hermes/sessions -name 'session_cron_*.json' -delete

# 删除旧用户会话（保留最近 30 天）
find ~/.hermes/sessions -name 'session_*.json' -mtime +30 -delete

# 清理旧 checkpoints（保留最近 5 个）
ls -1t ~/.hermes/checkpoints/ | tail -n +6 | xargs rm -rf
```

## 8. 领域目录验证

```bash
ls ~/quant/daily_kline_update.py       # 量化脚本
ls ~/PDD/pdd_listing_v3.py             # 电商脚本
ls ~/writing-data/scripts/             # 写作管线
ls ~/brain/graphify-out/graph.json     # 知识图谱
```

## 9. Camofox（可选）

迁移后 Camofox 大概率未安装：

```bash
# 如果不需要浏览器自动化，可以跳过
# 如果需要：
sudo apt install firefox-esr  # 或其他浏览器
# Camofox 需额外安装配置
```

## 10. 最终验证清单

- [ ] DeepSeek API key 有效
- [ ] Gateway 启动且 QQ Bot Ready
- [ ] web_search MCP 可用（测试搜 "test"）
- [ ] MySQL 连通
- [ ] 6 个 profile 目录存在
- [ ] Skills 数量 ≥ 150
- [ ] Cron jobs 列表正常
- [ ] sessions 已清理
- [ ] checkpoints 已清理
- [ ] .env 格式无行号污染
- [ ] K线数据已回填（或已排队）

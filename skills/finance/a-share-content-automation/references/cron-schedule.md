# Cron任务配置

## 时间线原则

**一致性**：所有内容生成任务的执行时间保持一致
- 数据采集/分析时间：15:30（收盘后30分钟）
- 通知推送时间：18:00（人工审核窗口）

---

## 标准Cron配置

### 交易日每日复盘（周一至周五）

#### 任务1：每日复盘生成（15:30）

```yaml
name: "A股每日复盘生成"
schedule: "30 15 * * 1-5"
enabled: true
deliver: "local"
```

**执行步骤**：
1. 采集今日A股数据（大盘/板块/个股）
2. 量化分析（技术指标+资金流向）
3. AI生成每日复盘文章
4. 保存到 `~/writing-data/drafts/YYYY-MM-DD-每日复盘.md`

#### 任务2：每日复盘通知（18:00）

```yaml
name: "A股每日复盘推送通知"
schedule: "0 18 * * 1-5"
enabled: true
deliver: "weixin:o9cq803IOaHaTL8F-jARLOmc4xOs@im.wechat"
```

**执行步骤**：
1. 检查 `~/writing-data/drafts/YYYY-MM-DD-每日复盘.md` 是否存在
2. 发送微信通知：
   ```
   【A股复盘已生成】
   文件位置: ~/writing-data/drafts/YYYY-MM-DD-每日复盘.md
   请审核后发布到微信公众号草稿箱
   ```

---

### 周末周总结（周六、周日）

#### 任务3：周总结分析生成（15:30）

```yaml
name: "A股周总结分析生成"
schedule: "30 15 * * 6,0"
enabled: true
deliver: "local"
```

**执行步骤**：
1. 确认今天是周末（周六或周日）或节假日
2. 扫描本周一至周五的 `~/writing-data/raw/` 目录
3. 检查交易日完整性（至少3个交易日）
4. 统计本周核心指标：
   - 指数周涨跌幅
   - 资金流向
   - 板块热度
5. 识别本周最热方向（1-2个板块/题材）
6. AI生成周总结文章（1500-2500字）
7. 保存到 `~/writing-data/drafts/YYYY-MM-DD-周总结.md`

**交易日不足处理**：
- 如果本周交易日<3个，不生成周总结
- 发送通知：`本周交易日不足，暂不生成周总结`

#### 任务4：周总结通知（18:00）

```yaml
name: "A股周总结推送通知"
schedule: "0 18 * * 6,0"
enabled: true
deliver: "weixin:o9cq803IOaHaTL8F-jARLOmc4xOs@im.wechat"
```

**执行步骤**：
1. 检查 `~/writing-data/drafts/YYYY-MM-DD-周总结.md` 是否存在
2. 如果存在，发送通知：
   ```
   【A股周总结已生成】
   文件位置: ~/writing-data/drafts/YYYY-MM-DD-周总结.md
   请审核后发布到微信公众号草稿箱
   ```
3. 如果不存在，发送通知：
   ```
   【周总结生成失败】
   未找到 ~/writing-data/drafts/YYYY-MM-DD-周总结.md
   请检查日志: ~/writing-data/publish-logs/
   ```

---

## Cron表达式说明

| 表达式 | 含义 | 示例 |
|--------|------|------|
| `30 15 * * 1-5` | 每周一至周五15:30 | 交易日每日复盘生成 |
| `0 18 * * 1-5` | 每周一至周五18:00 | 交易日每日复盘通知 |
| `30 15 * * 6,0` | 每周六日15:30 | 周末周总结生成 |
| `0 18 * * 6,0` | 每周六日18:00 | 周末周总结通知 |

---

## 实际配置示例

### 通过Hermes CLI创建

```bash
# 交易日每日复盘通知
hermes cron create \
  --name "A股复盘文章生成提醒" \
  --schedule "0 18 * * 1-5" \
  --deliver "weixin:o9cq803IOaHaTL8F-jARLOmc4xOs@im.wechat" \
  --prompt "检查~/writing-data/drafts/目录下是否存在今日复盘文件，存在则发送微信通知"
```

```bash
# 周末周总结生成
hermes cron create \
  --name "A股周总结分析生成（周末）" \
  --schedule "30 15 * * 6,0" \
  --deliver "local" \
  --prompt "分析本周数据，识别最热方向，生成周总结文章"
```

```bash
# 周末周总结通知
hermes cron create \
  --name "A股周总结推送通知（周末）" \
  --schedule "0 18 * * 6,0" \
  --deliver "weixin:o9cq803IOaHaTL8F-jARLOmc4xOs@im.wechat" \
  --prompt "检查周总结文件是否存在，存在则发送微信通知"
```

---

## Cron任务管理

### 查看所有任务

```bash
hermes cron list
```

### 查看任务详情

```bash
hermes cron show <job_id>
```

### 删除任务

```bash
hermes cron delete <job_id>
```

### 暂停/恢复任务

```bash
hermes cron pause <job_id>
hermes cron resume <job_id>
```

---

## 故障排查

### 任务未执行

**检查任务状态**：
```bash
hermes cron show <job_id>
```

**检查日志**：
```bash
journalctl -u hermes-cron -f
```

**常见原因**：
1. 任务被暂停 → `hermes cron resume <job_id>`
2. Cron服务未运行 → `systemctl restart hermes-cron`
3. 时间表达式错误 → 重新创建任务

### 通知未送达

**检查WeChat iLink gateway**：
```bash
systemctl status hermes-weixin-gateway
```

**重启gateway**：
```bash
systemctl restart hermes-weixin-gateway
```

**检查session是否过期**：
- 登录 `~/.hermes/weixin/` 目录
- 查看session文件时间戳
- 如过期，重新扫码登录

### 数据未生成

**检查数据目录**：
```bash
ls -lh ~/writing-data/raw/$(date +%F)
ls -lh ~/writing-data/drafts/
```

**检查执行日志**：
```bash
cat ~/writing-data/publish-logs/$(date +%F)-publish.log
```

**手动触发任务**：
```bash
hermes cron run <job_id>
```

---

## 最佳实践

### 1. 任务命名规范

**格式**：`功能+执行时间+类型`

**示例**：
- `A股复盘文章生成提醒`（18:00通知）
- `A股周总结分析生成（周末）`（15:30生成）
- `A股周总结推送通知（周末）`（18:00通知）

### 2. Prompt设计原则

**生成类任务Prompt**：
- 明确工具：`可用工具：terminal、execute_code、write_file、web_search`
- 分步骤：使用`1.、2.、3.`编号
- 明确输出：指定文件保存路径
- 今日日期：使用 `$(date +%F)` 或占位符

**通知类任务Prompt**：
- 简单判断：检查文件是否存在
- 清晰通知：模板化消息内容
- 异常处理：失败时提供日志路径

### 3. 时间选择

**数据采集时间**：
- 交易日：15:30（收盘后30分钟）
- 周末：15:30（与交易日一致）

**通知推送时间**：
- 交易日：18:00（下班后人工审核）
- 周末：18:00（与交易日一致）

### 4. 交付方式（deliver）

**本地执行**：`deliver: "local"`
- 适用于数据采集、文章生成

**微信通知**：`deliver: "weixin:o9cq803IOaHaTL8F-jARLOmc4xOs@im.wechat"`
- 适用于提醒通知

---

## 当前已配置任务（2026-05-05）

| Job ID | 名称 | Schedule | Delivered |
|--------|------|----------|-----------|
| 704e9bfe5896 | A股复盘文章生成提醒 | 0 18 \* \* 1-5 | weixin:o9cq803IOaHaTL8F-jARLOmc4xOs |
| 3858ff88add6 | A股周总结分析生成（周末） | 30 15 \* \* 6,0 | local |
| 0941df5e20bd | A股周总结推送通知（周末） | 0 18 \* \* 6,0 | weixin:o9cq803IOaHaTL8F-jARLOmc4xOs |

---

## 扩展场景

### 节假日判断

如需区分节假日，可在Prompt中添加：

```python
# 检查今天是否为交易日
import akshare as ak
import holidays

cn_holidays = holidays.CN()
today = datetime.date.today()

if today in cn_holidays:
    print("今天是节假日，跳过")
    sys.exit(0)
```

### 多时区支持

如需支持多时区用户，可在schedule中使用：

```yaml
schedule: "30 15 * * 1-5"  # CST (China Standard Time)
```

或使用UTC时间（+8小时计算）：

```yaml
schedule: "30 7 * * 1-5"  # UTC 07:30 = CST 15:30
```

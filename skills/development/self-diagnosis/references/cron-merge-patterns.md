# Cron 归并模式

当 cron 任务过多（>20）或 WeChat 投递密度过高导致 rate limiting 时，使用以下经过验证的归并模式。

## 模式1：早间归并（同时间段合并）

**场景**：多个任务在相近时间（如 08:00-08:30）都要投递 weixin。

**操作**：
1. 选最早的时间槽作为锚点
2. 将多个任务的 prompt 合并为一个（step1→step2→汇总）
3. 更新锚点 job，删除其余

**示例**：
```
之前：08:00 系统巡检(weixin) + 08:05 盘前信号(weixin)
之后：08:00 早间合并(weixin) → prompt内串联巡检+信号
```

## 模式2：晚间归并（同一投递目标合并）

**场景**：20:00-21:30 有多个 weixin 投递。

**操作**：
1. 选中间时间点（如 21:00）
2. 合并为一个 prompt：回测→信号扫描→汇总
3. 一次 weixin 投递输出全部结果

**示例**：
```
之前：20:30 回测 + 21:10 日报 + 21:30 信号(全部weixin)
之后：21:00 晚间合并(weixin) → 一次投递
```

## 模式3：周度归并（多时间槽合并）

**场景**：周一多个 graphify/审计任务在不同时间（03:00/05:00/06:00/07:00）。

**操作**：
1. 选最早时间（03:00）
2. 4个目标在一个 prompt 内顺序执行
3. 删除其余 3 个 cron

**示例**：
```
之前：03:00 wiki-graphify + 05:00 profiles + 06:00 skills + 07:00 quant
之后：03:00 graphify-四合一 → 顺序跑4个目标
```

## 模式4：降级投递（weixin→local）

**场景**：非紧急任务（cost report, watchdog, health check）不需要实时推送到微信。

**操作**：
```
cronjob action=update job_id=<id> deliver="local"
```

**适用**：
- 每小时/每30min 的高频任务
- 日报类（存本地，用户主动查看）
- 监控类（异常才告警，正常默默保存）

## 效果验证

归并后检查：
```bash
# 确认 WeChat 投递任务数
cronjob list | grep -c 'weixin:'

# 确认无 rate limit 残留
cronjob list | grep 'last_delivery_error.*rate limited'

# 确认时间窗口无重叠
cronjob list | grep 'weixin:' | grep -oP '\d+:\d+' | sort
```

**目标**：工作日 weixin 投递 ≤5 条，任意两条间隔 ≥2h。

# Cron失活恢复流程 (2026-05-13)

## 症状

Gateway重启（尤其是QQ Bot credential轮换后）可能导致：
1. `cron.db` 文件变为0字节
2. 部分cron在 `jobs.json` 中存在但不在active调度器列表中
3. `hermes cron list` 显示的数量远少于 `jobs.json` 中的定义数

## 诊断

```bash
# 对比active vs defined
hermes cron list 2>&1 | grep -c "^\s*[a-f0-9]"
python3 -c "import json; print(len(json.load(open('/home/pebynn/.hermes/cron/jobs.json'))['jobs']))"

# 找到失活的具体cron
python3 << 'PYEOF'
import json
with open('/home/pebynn/.hermes/cron/jobs.json') as f:
    all_ids = {j['id'] for j in json.load(f)['jobs']}
# 手动从 hermes cron list 提取active IDs...
active_ids = set(['15d19bd7a80f', ...])  # 填入实际active列表
inactive = all_ids - active_ids
print(f"失活: {len(inactive)}个 - {inactive}")
PYEOF
```

## 恢复

```bash
# 1. 逐个激活
hermes cron resume <cron_id>

# 2. 检查deliver目标（gateway重启后openid可能变化）
hermes cron list 2>&1 | grep -A3 "<cron_id>"

# 3. 若deliver仍是local → 更新为qqbot
hermes cron edit <cron_id> --deliver 'qqbot:NEW_OPENID'
# ⚠️ 注意：命令是 hermes cron edit，不是 hermes cron update
```

## 本次案例 (2026-05-13)

- 5个写作管线cron全部失活：cb4e13762bf2, e10e5bab3a4e, f54a3f9f759a, 79e67133f2d0, 11502faaf718
- 所有6个cron的deliver从 `local` 更新为 `qqbot:F8FEB3B1529A7281750E9547DE13F1EE`
- `3858ff88add6` (周总结) 未失活但也更新了deliver
- `003f607dffbf` (旧复盘) 从jobs.json中完全删除，无备份

## 预防

- 每次Gateway重启后运行诊断对比active vs defined
- `cron.db` 和 `jobs.json` 定期备份
- 关键cron配置纳入git（`~/.hermes/cron/jobs.json` 已在git中但被忽略？检查gitignore）

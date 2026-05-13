# Cron Wrapper Script 标准模式

## 模板

```bash
#!/bin/bash
# <用途说明> wrapper - 供cron调用

# 必须：设置HOME（cron环境可能没有）
export HOME=/home/pebynn

# 必须：设置PATH（确保找到Python和依赖）
export PATH="/home/pebynn/tools/quant_env/bin:/usr/local/bin:/usr/bin:/bin"

# 必须：cd到脚本工作目录
cd /home/pebynn/quant

# 必须：exec直调（避免bash子进程残留+减少开销）
exec /home/pebynn/tools/quant_env/bin/python3 /home/pebynn/quant/script_name.py
```

## 原则

1. **exec 而非 bash -c**：bash -c 产生子进程，cron runner需管理两层进程，增加超时风险
2. **不在wrapper中做复杂逻辑**：交易日检查、重试等放在Python脚本中
3. **统一存放路径**：所有wrapper放 `~/.hermes/scripts/`（cron script字段解析于此）
4. **设置HOME**：cron runner可能没有HOME环境变量，导致 `~/.finquant` 等路径解析失败

## 反模式（避免）

```bash
# ❌ 不要：多层bash嵌套
#!/bin/bash
bash -c "cd /home/pebynn/quant && python3 daily_kline_update.py"

# ❌ 不要：在wrapper里做复杂逻辑
if [ $(date +%u) -ge 6 ]; then exit 0; fi
# ...应该放在Python脚本中

# ❌ 不要：忘记设置HOME
cd /home/pebynn/quant && /home/pebynn/tools/quant_env/bin/python3 script.py
# cron环境没有HOME，~/.finquant/cache 解析失败
```

## 已使用此模式的cron

| cron | wrapper | 实际脚本 | 验证耗时 |
|:--|:--|:--|:--|
| `afff56398abe` (K线更新) | `~/.hermes/scripts/daily_kline_update.sh` | `~/quant/daily_kline_update.py` | ~64s |
| `0637e225e375` (信号生成) | `~/.hermes/scripts/run_daily_signals.sh` | `~/quant/run_daily_signals.sh` | ~112s |

## 关键约束

- **120s硬超时**: cron runner对no_agent脚本有120s硬超时（不是.env TERMINAL_TIMEOUT=600）
- **PATH解析**: cron script字段解析到 `~/.hermes/scripts/`，不是任务工作目录
- **exec only**: 用exec替换当前进程，不带`&`后台运行

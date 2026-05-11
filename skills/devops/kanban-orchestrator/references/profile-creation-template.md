# Profile Creation Template for Kanban Workers

## Directory Structure

```
~/.hermes/profiles/<profile-name>/
├── SOUL.md                # Worker role description
├── config.yaml            # Model + delegation config
├── skills/
│   └── devops/
│       └── kanban-worker/ # Only skill needed (bundled from main)
├── logs/
├── workspace/
└── sessions/
```

## SOUL.md Template

```markdown
# <profile-name> — <one-line role description>

> 自动生成 Kanban Worker 配置。由 kanban dispatcher 调度。

## 核心能力
<2-3 sentences describing what this worker does>

## 工作准则
1. 只做任务描述中的工作，不扩大范围
2. 完成即 kanban_complete，产出写入 workspace
3. 遇到问题 kanban_block 等待指挥
4. 不调用 delegate_task（kanban worker 内部规则）
```

## config.yaml Template

```yaml
model:
  default: deepseek-v4-pro    # or deepseek-v4-flash for mechanical workers
  provider: deepseek
  base_url: https://api.deepseek.com/v1
delegation:
  max_spawn_depth: 2
  max_concurrent_children: 3
  orchestrator_enabled: false  # leaf workers don't orchestrate
```

### Model Routing

| Worker Type | Model | Key |
|:--|:--|:--|
| Reasoning (writer/reviewer/finance/research) | deepseek-v4-pro | `default: deepseek-v4-pro` |
| Mechanical (ec-sourcing/listing/ops) | deepseek-v4-flash | `default: deepseek-v4-flash` |
| Coding (code-domain) | glm-5.1 | Needs glm provider config |

## Post-Creation Steps

1. **Copy kanban-worker skill**: `cp -r ~/.hermes/profiles/ops-domain/skills/devops/kanban-worker ~/.hermes/profiles/<name>/skills/devops/`
2. **Lock skills dir**: Run `scripts/lock_profile_skills.py <name>` to prevent auto-rebundle on first dispatch
3. **Verify**: Create a kanban smoke test task and check it completes
4. **Re-verify after first dispatch**: First dispatch triggers auto-bundle despite lock attempts. Re-run step 2 if needed.

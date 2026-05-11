# Hermes Config Audit — 实战模式库

本文件记录在审计执行中发现的真实模式，供未来审计代理参考。内容来自实际扫描发现的模式而非理论。

---

## 1. .env 凭证扫描 — 安全审计器的使用

**问题**：`read_file` 工具在显示 `.env` 时会自动遮盖敏感值（如 `DEEPSEEK_API_KEY=***`）。这种遮盖是**前端的视觉遮盖**，不代表文件没有明文 sk-* 密钥。

**解法**：使用 `mcp_security_auditor_scan_file` 扫描 `.env`，可以穿透遮盖看到真实的明文凭证。

```yaml
# read_file 显示：
DEEPSEEK_API_KEY=***
GITHUB_TOKEN=***

# security-auditor 检测到的真实内容：
[HIGH] Line 1: OpenAI/AI API Key (sk-...) detected: sk-676e0825...
[HIGH] Line 12: GitHub Personal Access Token (ghp_) detected: ghp_GJr4rl...
```

**执行顺序**：先 `security-auditor` 扫描，再用 `read_file`（带遮盖）给用户看报告。两个数据源并用。

**权限检查**：完成扫描后附带检查文件权限（`stat -c '%a %U:%G' ~/.hermes/.env`），正常应为 `600`。

---

## 2. 凭证残留在 state-snapshots/

**问题**：Hermes 升级或配置变更时，系统会在 `~/.hermes/state-snapshots/` 下生成快照，这些快照包含完整的 `.env`、`config.yaml` 等配置文件的旧版本副本。

**检查方式**：
```bash
find ~/.hermes -name '.env' -exec sh -c 'echo "{}: $(stat -c "%a %U:%G" "{}")"' \;
```

**典型发现**：
```
/home/pebynn/.hermes/.env: 600 pebynn:pebynn
/home/pebynn/.hermes/state-snapshots/20260430-063238-pre-update/.env: 600 pebynn:pebynn
```

**风险判断**：
- 快照中同文件权限为 600 → 风险低但冗余
- 快照中权限为 644 或更高 → HIGH，建议清理

**建议清理**（可安全删除旧快照）：
```bash
# 保留最近一次快照，删除更早的
ls -t ~/.hermes/state-snapshots/ | tail -n +2 | xargs -I {} rm -rf ~/.hermes/state-snapshots/{}
```

---

## 3. 已失效的平台残留 — gateway_state.json 分析

**问题**：`config.yaml` 中没有某个平台的任何配置（无 platform_toolsets，无 provider 段），但网关仍在尝试连接并报错。

**检查方式**：读取 `~/.hermes/gateway_state.json`，检查 `platforms` 段

```json
{
  "platforms": {
    "weixin": {
      "state": "connected",
      "error_code": null
    },
    "qqbot": {
      "state": "retrying",
      "error_code": "qq_connect_error",
      "error_message": "QQ startup failed: ...invalid appid or secret"
    }
  }
}
```

**分类标准**：
| state | 含义 | 操作 |
|-------|------|------|
| `connected` | 正常 | 不需要动 |
| `retrying` + 持续报错（>24h） | 凭证无效/缺失 | 标记为 P2残留，建议修复或禁用 |
| `disconnected` + 无 error | 已关闭但配置存在 | 标记为 P3 |
| 长期 `retrying` + gateway 进程重启后仍不停止 | 底层重试循环 | **P1** — 网关性能受影响 |

**QQ Bot 具体情况**（2026-04-27 起持续失败）：
- 凭证缺失（.env 无 QQ_* 变量）
- 网关自动重试，但永远无法成功
- 产生无用错误日志
- 建议：禁用 qqbot 平台或补全凭证

---

## 4. 数据库凭证嵌入 MCP Server 配置

**模式**：`config.yaml` 中 `mcp_servers` 段的连接字符串可能直接包含数据库密码。

```yaml
mcp_servers:
  mysql:
    args:
      - "mysql://stock:***@localhost:3306/stock_kline"
```

**检测方法**：在 `config.yaml` 中 grep 查找 `://` 后跟 `***` 或明文密码的模式。

**修复建议**：使用环境变量替换密码段：
```yaml
args:
  - "mysql://stock:${STOCK_DB_PASSWORD}@localhost:3306/stock_kline"
```

**注意**：即使显示的 `***` 看起来像被遮盖了，实际文件中可能是明文。用 `security-auditor` 验证。

---

## 5. 域 Profile 技能副本审计模式

### 大集合 vs 小集合
| Profile | 技能副本总数 | 过期数 | 孤立技能数 | 特征 |
|---------|-------------|--------|-----------|------|
| code-domain | 36 | 7 | 10 | github/* 工具 + security/* 自研 |
| ec-domain | 87 | 8 | 57 | 大量 in-house: apple, creative, mlops, media |
| ops-domain | 25 | 5 | 1 | 基本匹配主目录 |
| research-domain | 26 | 5 | 1 | 基本匹配主目录 |

**ec-domain 孤立技能典型类型**：
- apple/*（FindMy, Messages, Notes, Reminders）
- creative/*（ascii-art, p5js, excalidraw, manim-video, songwriting）
- mlops/*（axolotl, vllm, unsloth, dspy, etc.）
- media/*（ffmpeg, imagemagick）
- productivity/*（google-workspace, notion, linear, ocr）

### 跨 Profile 重复孤立项
- `webhook-subscriptions` — 存在于 code/ec/ops 三个 profile
- `jupyter-live-kernel` — 存在于 ec/research 两个 profile

### 典型过期旗舰技能
- `hermes-agent` — 主目录 37,840B vs profile 30,519B（落后 7KB+）
- `hermes-agent-skill-authoring` — 主目录 8,591B vs profile 7,583B

### 分叉风险（同名不同内容）
- `native-mcp` — 主目录 `development/` 下是 5,739B，profiles 的 `mcp/` 下是 12,330B。内容不同。

---

## 6. 安全审计器扫描范围建议

对于 `profiles/` 目录下的扫描，产量很大（~973 文件产生 ~4000 个发现项），建议带上路径过滤：

```bash
# 只扫关键文件
mcp_security_auditor_scan_file: ~/.hermes/.env
mcp_security_auditor_scan_file: ~/.hermes/config.yaml
mcp_security_auditor_scan_file: ~/.hermes/auth.json

# 扫 5 个 profile 的 config（通常干净）
mcp_security_auditor_scan_file: ~/.hermes/profiles/*/config.yaml

# 扫 SOUL.md — 可能会扫出疑似密钥但通常是 False Positive
# 因为 SOUL.md 中的 demo 密码/占位符会被误报
```

---

## 7. Profile Skills 大规模重复（v1.6 新增 — 2026-05-06 审计发现）

**发现**：5 个 profile 各含 56-92 个 skill 的完整副本，共 323 个 profile 实例 vs 108 个 master skill。其中 45 个副本内容与 master 不一致（stale copies）。

**检测命令**：
```bash
# 统计各 profile skill 数量
for d in ~/.hermes/profiles/*/skills/; do
  count=$(find "$d" -name "SKILL.md" | wc -l)
  echo "$(basename $(dirname $d)): $count skills"
done

# 检测过期副本（内容哈希 vs master）
python3 -c "
import os, hashlib
from pathlib import Path

master_dir = Path.home() / '.hermes' / 'skills'
profiles_dir = Path.home() / '.hermes' / 'profiles'

master_skills = {}
for f in master_dir.rglob('SKILL.md'):
    rel = f.relative_to(master_dir)
    name = str(rel.parent) if rel.parent != master_dir else 'root'
    master_skills[name] = hashlib.md5(f.read_bytes()).hexdigest()

stale = 0
for pf in profiles_dir.iterdir():
    skills_dir = pf / 'skills'
    if not skills_dir.exists(): continue
    for f in skills_dir.rglob('SKILL.md'):
        rel = f.relative_to(skills_dir)
        name = str(rel.parent) if rel.parent != skills_dir else 'root'
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if name in master_skills and h != master_skills[name]:
            stale += 1
            print(f'STALE: {pf.name}/{name}')

print(f'Total stale copies: {stale}')
"
```

**严重性判断**：
- writing-domain 有 92 skills（558 文件）— 占比最大，接近全量复制
- finance-domain 仅 7 skills — 最干净
- 同名 skill 在 6 个 profile 中各有一份（如 `imessage`, `himalaya`, `godmode`）— 完全冗余

**修复方向**：删除 profile 下 skills/ 目录，子代理改为从 master `~/.hermes/skills/` 加载。Profile 下只保留域专属的自建技能。

---

## 8. 非标准 config 字段检测（v1.6 新增）

**发现**：`delegation.default_model` 不是标准 Hermes delegation schema 字段。

**标准 delegation 字段**：`max_iterations`, `child_timeout_seconds`, `reasoning_effort`, `max_concurrent_children`, `max_spawn_depth`, `orchestrator_enabled`, `subagent_auto_approve`

**检测命令**：
```bash
grep -rn "default_model" ~/.hermes/profiles/*/config.yaml
```

**受影响文件**（2026-05-06）：
- `code-domain/config.yaml` line 8: `delegation.default_model: deepseek-v4-flash`
- `writing-domain/config.yaml` line 7: `delegation.default_model: deepseek-v4-flash`

**影响**：此字段可能完全不生效，导致子代理模型路由回退到域自身的 `model.default`。

**修复**：改为标准的 `model.default` 字段定义子代理模型，或确认 Hermes 版本是否支持此扩展字段。

---

## 9. 跨域 SOUL.md 段落重复（v1.6 新增）

**发现**：完全相同的规则段落在多个域 SOUL.md 中逐字重复，增加维护成本。

**检测命令**：
```bash
python3 -c "
from pathlib import Path
import hashlib

profiles = Path.home() / '.hermes' / 'profiles'
paragraphs = {}
for soul in sorted(profiles.glob('*/SOUL.md')):
    domain = soul.parent.name
    paras = [p.strip() for p in soul.read_text().split('\n\n') if len(p.strip()) > 80]
    for p in paras:
        h = hashlib.md5(p.encode()).hexdigest()
        paragraphs.setdefault(h, {'text': p[:120], 'domains': []})
        paragraphs[h]['domains'].append(domain)

for h, data in paragraphs.items():
    if len(data['domains']) >= 3:
        print(f'[{len(data[\"domains\"])} domains] {data[\"text\"]}...')
"
```

**已知案例**：\"任务前知识检索\"段（gbrain search + graphify query + 新领域标记 + context 纳入）在 code/ec/finance/ops/research 5 个域中完全相同。

**修复原则**：这类通用规则应只在主 SOUL.md 定义一次。域 SOUL.md 只保留域特有规则。

---

## 10. SOUL.md 结构完整性检查（v1.6 新增）

**标准段清单**（所有域 SOUL.md 应包含）：
- 核心能力 / 域身份
- 任务前知识检索
- 核心脚本
- 可用工具集
- 配合技能
- 协作规则
- 沟通风格

**检测**：
```bash
for f in ~/.hermes/profiles/*/SOUL.md; do
  name=$(basename $(dirname $f))
  echo "=== $name ==="
  for section in "任务前知识检索" "核心脚本" "协作规则" "沟通风格"; do
    grep -q "$section" "$f" && echo "  ✅ $section" || echo "  ❌ MISSING: $section"
  done
done
```

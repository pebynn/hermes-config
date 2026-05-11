# D-Layer Implementation — Sub-Agent Lesson Feedback

> 2026-05-08: 打通知识闭环的最后一块。子代理发现的新坑可回流传入教训系统。

## Problem

Before D-layer, the knowledge flow was one-way:
```
User corrects → [1.5] inject → sub-agent receives → sub-agent executes
                                    ↑
                         NO path for sub-agent to feed back new lessons
```

This meant: sub-agents encounter new pitfalls (API changes, data format shifts, React component updates) but those discoveries died with the session. Same pitfall hit again next time.

## Solution

Add `lessons:` as an optional field in the sub-agent response contract, and wire it into lesson_inject.

### Step 1: Update main SOUL.md delegate contract

```
# Before:
子代理返回必含 `status:`+`需要:`+`详情/路径:`

# After:
子代理返回必含 `status:`+`需要:`+`详情/路径:`+`lessons:`(可选，发现新坑时回传)
```

File: `~/.hermes/SOUL.md`, line 120

### Step 2: Update all 6 domain SOUL.md "协作规则" section

Each domain's SOUL.md needs the `lessons:` field instruction in their 协作规则 section. Use this patch template:

```
## 协作规则

按主 SOUL.md 协作契约格式返回（status/需要/详情）。
发现新坑/API变更/数据异常时，附加 `lessons:` 字段回传教训：
\`\`\`
lessons:
  - "一句话教训描述"
  - "具体参数/映射关系"
\`\`\`
```

Affected files:
- `~/.hermes/profiles/writing-domain/SOUL.md`
- `~/.hermes/profiles/code-domain/SOUL.md`
- `~/.hermes/profiles/finance-domain/SOUL.md`
- `~/.hermes/profiles/ec-domain/SOUL.md`
- `~/.hermes/profiles/ops-domain/SOUL.md`
- `~/.hermes/profiles/research-domain/SOUL.md`

Note: writing-domain's 协作规则 was slightly different (had old `learnings → ~/brain/agent/learnings/` line). Need to be careful with the old_text match.

### Step 3: Main agent processing logic

When main agent receives a response with `lessons:` field, it already auto-appends via the existing C-layer:

```python
# From SOUL.md Rule 6
python3 ~/.hermes/scripts/lesson_inject.py add \
    --domain {domain} --severity {severity} \
    --title "{title}" --body "{body}"
```

### Step 4: Mark D-layer as implemented in skill

Patch `agent-self-maintenance/SKILL.md`:
```
-| D | Sub-agent `lessons:` response field | ❌ Not yet implemented |
+| D | Sub-agent `lessons:` response field | ✅ |
```

## Verification

To verify D-layer is working:
1. Send a task to any domain that may discover an API change
2. Check sub-agent response for `lessons:` field
3. Verify `lesson_inject.py add` wrote to correct domain file
4. Confirm next delegation includes the new lesson in LESSON_BLOCK

## Related

- B-layer (lesson injection): `SOUL.md` instruction pipeline [1.5]
- C-layer (real-time learning): `SOUL.md` Rule 6, `lesson_inject.py`
- Cross-domain propagation: `~/.hermes/lessons/global.md`

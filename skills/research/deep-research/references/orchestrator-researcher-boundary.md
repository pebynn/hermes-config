# Orchestrator-Researcher Boundary

## The Split

The deep-research protocol has two distinct roles:

| Role | Who | What |
|:-----|:-----|:-----|
| **Orchestrator** (主代理) | Hermes 总指挥 | wiki_search → skill_view → delegate_task to research-domain → verify outputs → report |
| **Researcher** (子代理) | research-domain agent | Run full 9-lens protocol LIVE, write 4 output files, update wiki |

## Why This Split

The orchestrator is a scheduler, not an analyst. It cannot run the 9 lenses itself (越权规则). The researcher must run the lenses LIVE (not via background delegation) because:

1. The user wants to see the research process — live searches, visible reasoning, real-time synthesis
2. Background delegation is unreliable for reasoning-heavy tasks — subagents can get interrupted before completing all 9 lenses
3. The structured lens system benefits from mid-research course correction, which only works in live mode

## The Flow

```
User: "研究一下X"
  ↓
Orchestrator:
  1. mcp_llm_wiki_wiki_search X  ← check accumulated knowledge
  2. skill_view deep-research     ← load protocol
  3. Create ~/research-skill-graph/projects/X/  ← prepare directory
  4. delegate_task to research-domain:
     Goal: "Do deep research on X"
     Context: "Follow full 9-lens protocol. Write 4 output files to ~/research-skill-graph/projects/X/"
     Toolsets: [web, terminal, file, search, session_search, skills]
  ↓
Research-domain agent:
  5. Read deep-research skill (Step 0-8)
  6. Run all 9 lenses (live, visible to user)
  7. Write 4 files to project directory
  8. Update knowledge/concepts.md + knowledge/data-points.md
  9. Return: status + summary + paths
  ↓
Orchestrator:
  10. Verify 4 files exist
  11. Report executive summary + open-questions
```

## Common Failure Modes

1. **Orchestrator skips wiki_search** → starts fresh, loses accumulated knowledge. Fixed by SOUL.md hard trigger.
2. **Orchestrator tries to answer directly** → web_search twice, verbal conclusion. The anti-pattern.
3. **Researcher runs in background** → gets interrupted, incomplete lenses. Fixed by "live only" requirement.
4. **Orchestrator over-processes results** → rewrites, re-analyzes outputs. Violation of 加工边界 rule.

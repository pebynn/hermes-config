# Proactive: Domain Profile SKULL — ready chassis, needs content fill

## SOUL.md — Domain's Constitution

```yaml
---
name: <domain-name>
description: <one-liner: what this domain does>
version: 1.0.0
author: Hermes
license: MIT
---
```

**Constitution body** — after the YAML frontmatter:

```
# <Domain Title>

Domain positioning: <2-3 line positioning statement>

---

## Core responsibilities
1. <what this domain MUST do>
2. ...
3. ...

---

## Tooling (free-first)
| Tool       | Function                | Cost  | Access path         |
|------------|-------------------------|-------|---------------------|
| <tool>     | <what it does>          | free  | <URL/CLI function>  |

---

## Workflow protocol
### Input phase
<what triggers the domain>

### Processing phase
<step-by-step pipeline>

### Output phase
<what gets produced>

---

## Output specifications
| Output                | Content              | Path                        |
|-----------------------|----------------------|-----------------------------|
| <e.g. Daily report>   | <structure>          | ~/<domain-data>/<path>      |

---

## Constraints & red lines
### Platform compliance
### Quality standards
### Domain boundaries
```

---

## config.yaml — Domain wiring

```yaml
model:
  provider: deepseek
  model: deepseek-v4-flash
  temperature: 0.8

enabled_toolsets:
  - terminal
  - file
  - web

delegation:
  default_model: deepseek-v4-flash
  max_spawn_depth: 2
  timeout: 300

# Domain-specific config keys
# <add your config>

tracking:
  output_dir: ~/<domain-data>
  log_level: INFO
```

---

## Skill files — Sub-agent specializations

Each core workflow step gets its own `skills/<skill-name>/SKILL.md`:

```markdown
---
name: <domain>-<action>-<entity>
description: <what this skill does>
version: 1.0.0
author: Hermes
license: MIT
---

# <Skill Title>

## Trigger conditions
<when this skill is activated>

## Execution flow
### Step 1:
### Step 2:
...

## Tooling
| Tool           | Purpose |
|----------------|---------|
| terminal       | <why>   |
| file           | <why>   |

## Output specifications
### Required output
### Optional output

## Error handling
### Failure mode 1
### Failure mode 2

## Quality checklist
- [ ] Check 1
- [ ] Check 2
```

**Skill naming**: `<domain>-<action>-<entity>` — e.g. `a-share-data-collector`.  
Do NOT prefix the domain name into the skill name — skills describe **capabilities**, not ownership.

---

## README.md — User-facing guide

```
# <Domain Name> — User Guide

## Quick start
1. Configure API keys
2. Run `start.sh`
3. Use the domain

## Typical workflow
### Step 1: <user command>
### Step 2: <user command>

## Output locations
~/<domain-data>/

## Troubleshooting
### Problem 1
### Problem 2
```

---

## start.sh — Readiness check

Self-contained shell script that:
1. Checks directory structure exists
2. Validates API credentials are configured
3. Verifies all skill files are present
4. Reports ready/unready status with action items

```bash
#!/bin/bash
# Checks + prints status
```

---

## Data directory convention

```
~/<domain-data>/
├── raw/          # Raw input data
├── drafts/       # Generated outputs
├── publish-logs/ # Publication records
└── analysis/     # Optional intermediate analysis
```

The data directory path should be **stable and decoupled from the domain name**.  
If the domain gets renamed, data persists independently.

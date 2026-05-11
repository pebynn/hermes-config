---
name: prompt-optimizer
description: This skill should be used when users request help optimizing, improving, or refining their prompts or instructions for AI models. Use this skill when users provide vague, unclear, or poorly structured prompts and need assistance transforming them into clear, effective, and well-structured instructions that AI models can better understand and execute. This skill applies comprehensive prompt engineering best practices to enhance prompt quality, clarity, and effectiveness.
license: Complete terms in LICENSE.txt
---

# Prompt Optimizer

## Overview

This skill transforms user-provided prompts into high-quality, clear, and effective instructions optimized for AI models. Apply proven prompt engineering principles to enhance clarity, specificity, structure, and effectiveness.

## Two Operation Modes

### Mode A: Pipeline Mode (Silent Pre-processing) — DEFAULT in Hermes Agent

This skill runs as the **first stage** of the Hermes Agent instruction pipeline:

```
User instruction → optimize-and-clarify.py → {domain, priority, optimized_prompt} → context-assemble → delegate_task
```

**Pipeline stages**:
1. `optimize-and-clarify.py` (merged single-pass script): Optimizes raw input + classifies domain/priority/extracts constraints
2. `context-assemble` (brain layer): session_search + skill_view + mcp_graphify.graph_search → enriches delegation context
3. `delegate_task`: Dispatches to sub-agent with enriched context

Script: `~/.hermes/skills/development/prompt-optimizer/scripts/optimize-and-clarify.py`

In pipeline mode:
- **No analysis or output shown to user** — optimization happens silently
- The merged script replaced the old two-step `prompt-optimizer → task-clarify.py` flow
- Output JSON: `{optimized_prompt, domain, priority, goal, constraints, expected_output}` — feeds directly into context-assemble
- This is the **mandatory, always-on** mode for the Hermes main agent

### Mode B: Explicit Mode (User-facing)

Activate explicit mode when users:
- Explicitly request prompt optimization or improvement ("帮我优化这段指令")
- Ask for help making their requests more effective
- Request guidance on how to better communicate with AI models
- Want to see the optimization analysis and improvements

## Optimization Workflow

### Step 1: Analyze the Original Prompt

Examine the user's prompt and identify:

**Clarity issues:** Ambiguous terms, implicit assumptions, missing context
**Specificity gaps:** Undefined constraints, missing success criteria, unclear scope
**Structure problems:** Disorganized format, missing logical flow
**Format considerations:** No output format, unclear tone/style/length
**Complexity assessment:** Too complex for single prompt? Would prompt chaining help?

### Step 2: Identify the Core Intent

- What is the user trying to accomplish?
- What problem are they solving?
- What constitutes success?
- Who is the audience?

### Step 3: Apply Optimization Principles

- **Clarity**: State requirements explicitly, remove ambiguity
- **Context**: Explain WHY requirements matter, include background
- **Specificity**: Define constraints (length, format, scope), specify audience
- **Structure**: Organize logically, use sections/numbers, separate concerns
- **Examples**: Show input-output for complex formats
- **Honesty**: Allow "I don't know", prevent hallucination

### Step 4: Consider Advanced Techniques

- **Chain of Thought**: For reasoning/analysis tasks
- **Prefilling**: For strict format requirements (JSON, XML)
- **Prompt Chaining**: Break complex tasks into sequential steps
- **Structured Output**: Specify exact format, provide schemas

### Step 5: Deliver the Optimized Prompt

**Pipeline Mode (default)**: Output the optimized JSON directly — no analysis, no explanation. Feed into context-assemble then delegate_task.

**Explicit Mode**: Present in this format:

**Analysis Section:**
```
Original prompt issues identified:
- [List key problems]
```

**Optimized Prompt:**
```
[Complete optimized prompt in code block]
```

**Improvement Explanation:**
```
Key improvements made:
- [Major enhancements]
- [Added specificity]
- [Structural changes]
```

### Step 6: Iterate Based on Feedback

- Offer to adjust tone, length, specificity
- Provide alternatives if requested
- Refine based on user feedback

## Quality Standards

Every optimized prompt must include:
- [ ] Clear, unambiguous objective
- [ ] Sufficient context
- [ ] Specific constraints and requirements
- [ ] Target audience or use case
- [ ] Expected output format
- [ ] Quality criteria or success definition
- [ ] Permission to express uncertainty (when appropriate)

## Common Optimization Patterns

**Pattern 1: Vague → Specific Structured Task**
**Pattern 2: Implicit Context → Explicit Context**
**Pattern 3: Single Complex Prompt → Prompt Chain**
**Pattern 4: Generic Output → Formatted Output**
**Pattern 5: Assumed Constraints → Stated Constraints**

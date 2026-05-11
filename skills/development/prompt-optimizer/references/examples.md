# Prompt Optimization Examples

This document provides before-and-after examples of prompt optimization across different use cases.

## Example 1: Vague → Specific

### Before
> Write about marketing.

### After
> Write a 500-word blog post about B2B content marketing strategies for SaaS companies targeting small businesses (10-50 employees). Focus on practical, budget-friendly tactics. Include 3 specific tactics with implementation steps. Tone: professional but conversational. Output in Markdown with H2 headers for each tactic.

## Example 2: Implicit → Explicit Context

### Before
> Review this code and suggest improvements.

### After
> Review this Python script (attached). It processes customer orders from a CSV file and generates invoices. The main concerns are: (1) error handling for malformed CSV rows, (2) performance with 100K+ rows, (3) security of file path handling. Suggest improvements in priority order (critical → nice-to-have). Format each suggestion as: Problem → Impact → Fix.

## Example 3: Complex → Chained

### Before
> Research our competitors, analyze their pricing, suggest our new pricing strategy, create a pricing page draft, and estimate revenue impact.

### After (3-step chain):

**Step 1:**
> Research top 5 competitors in the project management SaaS space (Asana, Monday, ClickUp, Wrike, Notion). For each: list pricing tiers, key features per tier, target customer segment, and any recent pricing changes. Output as a comparison table.

**Step 2:**
> Using the competitor research from Step 1, propose a pricing strategy for our new project management tool. Our differentiator: unlimited integrations on all plans. Suggest 3 tiers (Starter/Pro/Enterprise), price points, and feature differentiation. Justify each tier relative to competitors.

**Step 3:**
> Based on the pricing strategy from Step 2, draft a pricing page. Include: tier comparison table, FAQ section (5 questions), and a compelling headline/description for each tier. Estimate potential revenue impact assuming 1000 Starter, 300 Pro, 50 Enterprise customers/month.

## Example 4: Generic → Formatted

### Before
> Give me a summary of the quarterly meeting notes.

### After
> Summarize the Q1 2026 meeting notes. Output as JSON with this structure:
> ```json
> {
>   "key_decisions": ["decision 1", "decision 2"],
>   "action_items": [{"owner": "name", "task": "description", "deadline": "date"}],
>   "risks_identified": ["risk with impact level"],
>   "next_meeting": "date and focus"
> }
> ```

## Example 5: No Constraints → Full Constraints

### Before
> Help me write a job description.

### After
> Write a job description for a Senior DevOps Engineer. Requirements:
> - Length: 800-1000 words
> - Sections: About Us, Role Overview, Responsibilities (5-7), Requirements (5-7), Nice to Have (3-4), Benefits
> - Tech stack: AWS, Kubernetes, Terraform, CI/CD (GitHub Actions)
> - Company: Series B startup, 50 employees, remote-first
> - Tone: Professional but not corporate, highlight autonomy and impact
> - Do NOT include: salary range (we'll add manually), application instructions

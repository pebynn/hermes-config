# Prompt Engineering Best Practices

This reference document contains comprehensive best practices for crafting effective prompts for AI models like Claude.

## Core Principles

### 1. Be Clear and Direct
- State exactly what you want
- Avoid ambiguous terms
- Use concrete, specific language
- Don't assume the AI will infer your intent

### 2. Provide Context
- Explain the use case and goals
- Describe the target audience
- Include relevant background information
- State WHY certain requirements matter

### 3. Define Constraints
- Specify output format (Markdown, JSON, etc.)
- Set length limits (word count, sections)
- Define tone and style
- State what to include AND exclude

### 4. Structure Matters
- Use clear section headers
- Separate instructions from context
- Use numbered lists for sequential steps
- Use bullet points for parallel requirements

### 5. Include Examples
- Show desired output format with examples
- Demonstrate edge case handling
- Provide input-output pairs for complex tasks

### 6. Allow Uncertainty
- Explicitly permit "I don't know" responses
- Ask for confidence levels
- Request acknowledgment of limitations
- Prevent hallucination by encouraging honesty

## Advanced Techniques

### Chain of Thought (CoT)
- Ask the model to think step by step
- Use structured format: reasoning → answer
- Effective for math, logic, analysis tasks
- Example: "First, analyze the problem. Then, list possible solutions. Finally, recommend the best approach."

### Prefilling
- Pre-populate the assistant's response
- Use for strict format enforcement
- Example: Starting with `{` for JSON output
- Eliminates unwanted preambles

### Prompt Chaining
- Break complex tasks into sequential steps
- Each step builds on previous output
- Reduces errors on multi-stage tasks
- Example: Research → Analysis → Summary → Action Plan

### Structured Output
- Specify exact format (JSON schema, XML, table)
- Use delimiters for sections
- Provide templates for the model to fill
- Example: "Return JSON with keys: title, summary, action_items"

### Role Assignment
- Assign a specific persona or expertise
- Example: "You are a senior software architect..."
- Helps frame responses appropriately

## Troubleshooting

### Issue: Model ignores constraints
- Make constraints more explicit
- Use negative examples (what NOT to do)
- Try prefilling to lock in format

### Issue: Hallucination or made-up facts
- Add "If uncertain, say so explicitly"
- Request citations or sources
- Use "Only use information from the provided context"

### Issue: Responses too long/short
- Specify exact word count or section count
- Use "Be concise" or "Be thorough" as needed
- Provide example of desired length

### Issue: Wrong tone or style
- Specify tone explicitly (formal, casual, technical)
- Provide a style sample
- Use "Write in the style of..." with examples

## Quality Checklist

Before finalizing any prompt, verify:
- [ ] Objective is clear and unambiguous
- [ ] Sufficient context is provided
- [ ] Specific constraints are stated
- [ ] Output format is specified
- [ ] Success criteria are defined
- [ ] Edge cases are addressed
- [ ] Uncertainty is handled

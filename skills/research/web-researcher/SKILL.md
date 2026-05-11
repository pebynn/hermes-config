---
author: unknown
description: Use this skill for deep research, fact-checking, or finding the latest
  technical news.
name: web-researcher
version: 1.0.0
---

# Web Researcher Skill

## When to use
- Use when the user asks for "the latest," "news," or "research" on a topic.
- Use when you need to verify a fact that isn't in your local training data.

## Research Protocol
1. **Multi-Query Search**: Don't just search once. Run 2-3 targeted searches (e.g., "OpenClaw 2026.3.2 features" AND "OpenClaw 2026.3.2 bugs").
2. **Deep Dive**: Use `web_fetch` on at least the top 2 most relevant URLs to get the full text. Snippets are not enough for deep research.
3. **Synthesis**: Summarize the findings by grouping them into "Key Facts," "Timeline," and "Contradictions" (if any).
4. **Cite Sources**: Always list the URLs you actually read at the end of your report.

## Content Extraction Protocol (Progressive Fallback)

When you need full page content, try in order:

1. **`web_extract(url)`** — Fastest, built-in. Works for most pages.
2. **Jina Reader** — If `web_extract` returns empty or garbled:
   ```bash
   curl -s "https://r.jina.ai/https://target-url"
   ```
   Supports image captions (`-H "X-With-Generated-Alt: true"`), JSON mode (`-H "Accept: application/json"`), and SPA pages.
3. **Crawl4AI** — If both above fail (heavy JS, anti-bot, deep crawl):
   ```python
   from crawl4ai import AsyncWebCrawler
   async with AsyncWebCrawler() as crawler:
       result = await crawler.arun(url="...")
       print(result.markdown)
   ```
4. **Camofox browser** — If all else fails (stealth Firefox, persistent session):
   Use `browser_navigate` via Camofox on localhost:9377 (CDP URL configured).

## Output Format
- Start with a 🪐 **Jupiter Research Brief** header.
- Use bullet points for readability.
- Highlight any "Breaking News" or "Critical Alerts" in bold.

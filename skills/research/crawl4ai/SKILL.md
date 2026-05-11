---
allowed-tools:
- terminal
- file
- web
author: unknown
description: Open-source LLM-friendly web crawler & scraper. Async browser pool, smart
  Markdown, structured extraction, anti-detection. Falls back when web_extract and
  Jina Reader both fail.
execution: manual
name: crawl4ai
trigger:
- web_extract and Jina Reader both fail on complex pages
- need structured data extraction (CSS/XPath schemas)
- need deep crawling (multiple pages)
- need LLM-driven content extraction
version: 1.0.0
---

# Crawl4AI — LLM-Friendly Web Crawler & Scraper

## What It Is

[Crawl4AI](https://github.com/unclecode/crawl4ai) is an open-source web crawler optimized for LLM consumption. Generates clean Markdown, supports structured extraction, anti-detection, and can be deployed locally or via Docker.

**Installed at:** Hermes venv (`crawl4ai 0.8.6`)

## When to Use

- `web_extract` + Jina Reader both return incomplete content
- Need structured JSON extraction from repetitive pages (product listings, prices)
- Need deep crawl (follow links across multiple pages)
- Page has aggressive anti-bot protection
- Need fit-Markdown with BM25 content filtering

## Usage Patterns

### Pattern 1: Basic Markdown Extraction (Python)

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")
        print(result.markdown)  # Clean Markdown

asyncio.run(main())
```

### Pattern 2: Fit Markdown (noise removal)

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

run_config = CrawlerRunConfig(
    cache_mode=CacheMode.ENABLED,
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed")
    ),
)

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com", config=run_config)
        print(result.markdown.fit_markdown)

asyncio.run(main())
```

### Pattern 3: Structured Data Extraction (CSS Schema)

```python
from crawl4ai import AsyncWebCrawler, JsonCssExtractionStrategy

schema = {
    "name": "Product Listings",
    "baseSelector": ".product-item",
    "fields": [
        {"name": "title", "selector": "h2.title", "type": "text"},
        {"name": "price", "selector": "span.price", "type": "text"},
        {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"},
    ]
}

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com/products",
            extraction_strategy=JsonCssExtractionStrategy(schema)
        )
        print(result.extracted_content)

asyncio.run(main())
```

### Pattern 4: CLI Usage

```bash
# Basic markdown
crwl https://example.com -o markdown

# With extraction query
crwl https://example.com/products -q "Extract all product names and prices"

# Deep crawl
crwl https://example.com --deep-crawl bfs --max-pages 5
```

### Pattern 5: Docker Deployment (if needed)

```bash
docker pull unclecode/crawl4ai:latest
docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g unclecode/crawl4ai:latest

# Then use HTTP API
curl -X POST "http://localhost:11235/crawl" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "priority": 10}'
```

## Integration Pattern (Progressive Fallback)

When needing content from a URL, try in order:

1. `web_extract(url)` — fastest, built-in
2. `terminal("curl 'https://r.jina.ai/...'")` — Jina Reader API (no deps)
3. Python script using Crawl4AI — most powerful, handles anything

## Pitfalls

- First run needs Playwright browsers download (auto on first use, may need proxy)
- Heavy dependency (~50 packages installed); keep for complex tasks only
- `crawl4ai-setup` may need network access for Playwright browser download
- Chinese sites: use local Playwright browser, not Docker (Docker may be in US regions)
- If `playwright install` fails, use: `python -m playwright install chromium --with-deps`

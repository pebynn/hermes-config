---
allowed-tools:
- web_search
- web_extract
- terminal
author: unknown
description: Convert any URL to LLM-friendly Markdown via r.jina.ai. Free API, no
  key needed. Falls back to Jina Reader when web_extract fails on dynamic/complex
  pages.
execution: auto
name: jina-reader
trigger:
- web_extract returns incomplete/empty content
- page requires JavaScript rendering
- need cleaner markdown output than web_extract provides
version: 1.0.0
---

# Jina Reader — URL to LLM-friendly Markdown

## What It Is

[Jina Reader](https://github.com/jina-ai/reader) is a free API service by Jina AI that converts any URL to clean, LLM-friendly Markdown. No API key needed, no rate limits for normal use.

Base URLs:
- Read: `https://r.jina.ai/https://<target-url>`
- Search: `https://s.jina.ai/<search-query>`

## When to Use

- `web_extract` returns empty or garbled content
- Page is a SPA (Single Page Application) with client-side rendering
- Need cleaner Markdown (better table/code block formatting)
- Need image captioning (via `X-With-Generated-Alt` header)
- Need to search the web with top-5 result extraction

## Usage

### Basic Read (like web_extract but better on dynamic pages)

```bash
curl -s "https://r.jina.ai/https://example.com/page"
```

Returns clean Markdown of the page content.

### Search + Read (top 5 results)

```bash
curl -s "https://s.jina.ai/search+query+here"
```

Searches the web, fetches top 5 results, returns each as Markdown.

### With Image Captions

```bash
curl -s -H "X-With-Generated-Alt: true" "https://r.jina.ai/https://example.com"
```

Generates alt-text for images that lack it via VLM.

### JSON Mode

```bash
curl -s -H "Accept: application/json" "https://r.jina.ai/https://example.com"
```

Returns `{"url": "...", "title": "...", "content": "..."}`.

### Streaming Mode

```bash
curl -s -H "Accept: text/event-stream" "https://r.jina.ai/https://example.com"
```

### Focus on Specific Element

```bash
curl -s -H "X-Target-Selector: #main-content" "https://r.jina.ai/https://example.com"
```

### In-Site Search

```bash
curl -s "https://s.jina.ai/query?site=example.com"
```

## Integration Pattern

When `web_extract` fails on a page:

1. First try: `web_extract(url)` — fast, built-in
2. Fallback: `terminal("curl -s 'https://r.jina.ai/https://...'")` — Jina Reader
3. For search: `terminal("curl -s 'https://s.jina.ai/query'")` — replaces multi-step web_search

## Pitfalls

- Chinese sites may be blocked or slow from r.jina.ai (US-based servers)
- Very large pages may timeout; use `X-Timeout` header to extend: `-H "X-Timeout: 30"`
- Respect robots.txt — Reader does on its end
- Use `X-No-Cache: true` for fresh content

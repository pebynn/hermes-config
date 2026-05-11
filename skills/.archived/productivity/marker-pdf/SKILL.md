---
name: marker-pdf
description: Convert PDF to clean Markdown/JSON/HTML with high accuracy. Handles tables, math, code, forms. Uses ML models (first run downloads ~2GB models).
version: 1.0.0
author: Hermes Community
allowed-tools:
  - terminal
  - file
trigger:
  - convert PDF to Markdown
  - extract tables from PDF
  - OCR scanned PDFs
execution: manual
---

# Marker — PDF to Markdown/JSON Converter

## What It Is

[Marker](https://github.com/datalab-to/marker) converts PDFs to clean Markdown with high accuracy. Handles tables, math (LaTeX), code blocks, headers/footers. Powers 200M+ pages/week at Datalab.

**Installed at:** `~/.local/bin/marker_single` (uses Python 3.12)

> ⚠️ **First run downloads ~2GB ML models.** Run a test conversion first:
> ```bash
> marker_single some_small.pdf --output_dir /tmp/test_marker
> ```

## Usage

### Single File

```bash
marker_single input.pdf --output_dir ./output
```

Options:
- `--page_range "0,5-10,20"` — convert specific pages
- `--output_format [markdown|json|html|chunks]` — output format
- `--use_llm` — enhance accuracy with LLM (Gemini/Claude/OpenAI)
- `--force_ocr` — force OCR for scanned PDFs
- `--disable_image_extraction` — skip images

### Multiple Files

```bash
marker input_dir/ --output_dir ./output --workers 4
```

### LLM-Enhanced Mode

```bash
marker_single input.pdf --output_dir ./output --use_llm
```

Needs `GEMINI_API_KEY` or `CLAUDE_API_KEY` or `OPENAI_API_KEY` env var.

### From Python (in Hermes scripts)

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

converter = PdfConverter(
    artifact_dict=create_model_dict(),
)
rendered = converter("document.pdf")
print(rendered.markdown)  # Clean Markdown
```

## Integration Pipeline

```
PDF → Marker(high-accuracy markdown) → Pandoc(DOCX/EPUB/HTML)
```

## Pitfalls

- First run: downloads Surya OCR models (~2GB); internet required
- GPU recommended for batch processing; CPU works but slower
- `--use_llm` mode needs an LLM API key (Gemini free tier works)
- For scanned PDFs, add `--force_ocr`

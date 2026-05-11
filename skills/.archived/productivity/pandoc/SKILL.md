---
name: pandoc
description: Universal document converter. Convert between Markdown, HTML, LaTeX, PDF, DOCX, EPUB, and 30+ formats.
version: 1.0.0
author: Hermes Community
allowed-tools:
  - terminal
trigger:
  - convert documents between formats
  - generate PDF from Markdown
  - convert DOCX/EPUB to Markdown
execution: auto
---

# Pandoc — Universal Document Converter

## What It Is

[Pandoc](https://pandoc.org) is the "Swiss Army knife" of document conversion. Installed at version **3.1.3**.

## Common Conversions

```bash
# Markdown → DOCX
pandoc input.md -o output.docx

# Markdown → PDF (needs LaTeX)
pandoc input.md -o output.pdf --pdf-engine=xelatex

# DOCX → Markdown
pandoc input.docx -o output.md

# EPUB → Markdown
pandoc input.epub -o output.md

# HTML → Markdown
pandoc input.html -o output.md

# Markdown → EPUB
pandoc input.md -o output.epub

# Multiple files → single output
pandoc chapter1.md chapter2.md -o book.epub

# With table of contents
pandoc input.md -o output.docx --toc

# With custom template
pandoc input.md --template=mytemplate.tex -o output.pdf
```

## Integration with Marker

Pipeline: PDF → Marker(markdown) → Pandoc(DOCX/EPUB)

```bash
marker_single input.pdf --output_dir ./output
pandoc ./output/input.md -o result.docx
```

## Pitfalls

- PDF output needs LaTeX installed (`sudo apt install texlive-xetex`)
- Chinese text in PDF needs `--pdf-engine=xelatex` and Chinese fonts
- Complex DOCX layouts may lose formatting; prefer Markdown round-trip

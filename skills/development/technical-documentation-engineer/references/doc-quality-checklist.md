---
title: Documentation Quality Checklist
description: Machine-readable checklist for auditing documentation quality
version: 1.0.0
categories:
  completeness:
    description: Does the doc cover everything it should?
    checks:
      - id: has-project-name
        description: README has an H1 project name
        severity: error
        weight: 10
      - id: has-one-line-desc
        description: README has a one-line description
        severity: error
        weight: 10
      - id: has-why-section
        description: Has a "Why" or motivation section
        severity: warning
        weight: 8
      - id: has-quickstart
        description: Has a Quick Start / Getting Started section
        severity: error
        weight: 10
      - id: has-installation
        description: Has an Installation/Setup section
        severity: error
        weight: 10
      - id: has-usage-examples
        description: Has usage examples with code
        severity: warning
        weight: 8
      - id: has-api-reference
        description: Has API reference (inline or linked)
        severity: warning
        weight: 6
      - id: has-config-table
        description: Configuration options documented in a table
        severity: suggestion
        weight: 4
      - id: has-contributing
        description: Has contributing guidelines (linked or inline)
        severity: suggestion
        weight: 3
      - id: has-license
        description: Has license information
        severity: warning
        weight: 5
      - id: has-error-docs
        description: API errors are documented with codes and meaning
        severity: suggestion
        weight: 4
      - id: has-prerequisites
        description: Prerequisites clearly listed
        severity: warning
        weight: 6
      - id: has-next-steps
        description: Has "Next Steps" or further reading section
        severity: suggestion
        weight: 3

  accuracy:
    description: Is the doc technically correct and up to date?
    checks:
      - id: code-samples-run
        description: Every code sample compiles/runs correctly
        severity: error
        weight: 15
      - id: cli-flags-correct
        description: CLI flags and arguments match actual implementation
        severity: error
        weight: 10
      - id: urls-resolve
        description: All URLs resolve to the correct target
        severity: error
        weight: 10
      - id: version-consistent
        description: Software version in docs matches current release
        severity: warning
        weight: 8
      - id: screenshots-current
        description: Screenshots match current UI/UX
        severity: warning
        weight: 6
      - id: config-defaults-match
        description: Default values match actual defaults
        severity: error
        weight: 10

  freshness:
    description: Is the content well-maintained and current?
    checks:
      - id: last-reviewed
        description: Last reviewed date is within 6 months
        severity: warning
        weight: 8
      - id: changelog-aligned
        description: Recent changelog entries reflected in docs
        severity: warning
        weight: 6
      - id: deprecated-removed
        description: Deprecated features are flagged or removed
        severity: warning
        weight: 7
      - id: migration-guide
        description: Breaking changes have a migration guide
        severity: error
        weight: 10

  clarity:
    description: Is the doc clear and well-structured?
    checks:
      - id: consistent-heading
        description: Heading hierarchy is logical (no jumps from H1 to H4)
        severity: warning
        weight: 5
      - id: code-lang-tags
        description: All code blocks have language tags
        severity: warning
        weight: 5
      - id: to-the-point
        description: Content is concise — no filler paragraphs
        severity: suggestion
        weight: 3
      - id: examples-realistic
        description: Code examples use realistic variable/domain names
        severity: suggestion
        weight: 3
      - id: error-messages
        description: Error messages include troubleshooting guidance
        severity: suggestion
        weight: 3
      - id: term-consistency
        description: Terminology is consistent throughout
        severity: warning
        weight: 4
      - id: tone-consistent
        description: Tone is consistent (second person, active voice)
        severity: suggestion
        weight: 2
---

# Documentation Quality Checklist

Use this checklist when auditing or reviewing documentation. Each check has a
severity (error, warning, suggestion) and weight (1-15). A document passing all
error-level checks and 80% of warning-level checks is considered passing.

## Quick Scoring

- **Error** checks: must all pass. Missing any = fail.
- **Warning** checks: aim for 80%+ pass rate.
- **Suggestion** checks: aim for 50%+ pass rate.

## How to Use

### With doc-audit.py

The `doc-audit.py` script automatically checks completeness and freshness
items. Run it on your project directory:

```bash
python3 scripts/doc-audit.py /path/to/project
```

### Manual Review

For accuracy and clarity items, manual review is recommended. Use the YAML
frontmatter above as a structured input for automated tools.

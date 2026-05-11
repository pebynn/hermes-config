# Secrets Scan Report — Session Example (2026-05-10)

This is a real scan execution example showing the full methodology: multi-directory parallel grep, severity triage, and structured reporting.

## Scope Scanned

- `/home/user/writing-data/scripts/` — 11 .py files
- `/home/user/quant/` — 48 .py files (recursive)
- `/home/user/.hermes/scripts/` — 42 .py files

## Pattern Groups Executed

| # | Pattern | Purpose |
|---|---------|---------|
| 1 | `(password\|secret\|token\|api[_-]?key)...=['\"]...['\"]` | Hardcoded credential assignments |
| 2 | `os.environ.get(...['\"][^'\"]+['\"])` | Env var fallback defaults |
| 3 | `sk-\|ghp_\|gho_\|AKIA\|xox[baprs]-` | Known key format suffixes |
| 4 | `-----BEGIN.*?KEY-----` | PEM private key blocks |
| 5 | `pymysql.connect\|create_engine` + context | DB connection strings |
| 6 | URL with `?token=\|?key=\|?password=` | Credentials in URL query params |
| 7 | `['\"](secret\|password\|token)['\"]: ['\"][^'\"]+['\"]` | Dict key-value secrets |

## Report Structure

Each finding:

```
**FINDING N — SEVERITY: Description**
- File: `/path/to/file.py`, line N
- `password="stock123"`  (context + 1 line)
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Recommendation: Load from environment variable or credential file
```

## Notable Patterns Observed

- `***` in connection strings is a redaction pattern — report as clean, not a finding
- Multiple files sharing the same DB config should be consolidated into one central config -> import model
- `sk-` prefix is NOT exclusive to OpenAI; treat any `sk-` string as a potential API key
- Empty string passwords (`password=""`) for root/superuser are MEDIUM severity — local-only risk but dangerous if exposed

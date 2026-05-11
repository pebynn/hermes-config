# ZAI / GLM Provider Quirks

## Base URL Path Variants

Z.AI (智谱) API has two known base URL path variants:

| Path | Where Found | Notes |
|------|-------------|-------|
| `https://api.z.ai/api/paas/v4` | config.yaml (manual), GLM docs | Standard API endpoint |
| `https://api.z.ai/api/coding/paas/v4` | auth.json (auto-populated) | Coding-specific subpath, auto-detected by Hermes |

When rotating GLM keys, verify both config.yaml and auth.json use the **same** base_url path. The `/api/coding/paas/v4` variant may work for coding-specific models but the standard `/api/paas/v4` is the documented endpoint.

## Key Format

GLM API keys are dot-separated: `<hex_part>.<base64_part>`
- Example: `334705b1d9c147c7a3c2b3e21d7db02a.EH6qbfqR84AqJQwc`
- First segment: 32 hex chars
- Second segment: variable-length base64-like string
- Total length: ~49 characters

## Exhaustion Behavior

ZAI returns HTTP 429 with message "Insufficient balance or no resource package. Please recharge." when the account balance is depleted. Unlike 401 (invalid key), a 429 exhaustion persists in auth.json's `last_status: "exhausted"` and blocks the new key from being used. Clearing all error fields is mandatory:

- `last_status`: "exhausted" → "active"
- `last_error_code`: 429 → null
- `last_error_reason`: "1113" → null
- `last_error_message`: full message → null

## Provider Config in config.yaml

```yaml
providers:
  zai:
    api_key: $GLM_API_KEY
    base_url: https://api.z.ai/api/paas/v4
```

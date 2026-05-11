# China API Provider Fallback Reference

Last verified: 2026-05-07. Provider landscape changes fast — re-verify before
committing a new provider to config.

## DeepSeek

- **Endpoint**: `https://api.deepseek.com/v1`
- **Stability**: Generally good, but ~20% intermittent connection drops observed
  from China-based Ubuntu server (May 2026). 2/10 pings timed out or exceeded 4s.
- **Models**: deepseek-v4-pro (reasoning, always CoT), deepseek-v4-flash (fast/cheap),
  deepseek-chat (legacy)
- **Auth**: `$DEEPSEEK_API_KEY` in Bearer header
- **Verdict**: Primary provider, but must have cross-provider fallback.

## Z.ai (智谱 gateway via Z.ai)

- **Endpoint**: `https://api.z.ai/api/paas/v4`
- **Stability**: **UNREACHABLE from China** (connection timeout, 5s+).
  Z.ai appears to route through non-China infrastructure.
- **Auth**: Same `$GLM_API_KEY` as 智谱 direct.
- **Verdict**: DO NOT USE. Use 智谱 direct instead.

## 智谱 Direct (Zhipu / BigModel)

- **Endpoint**: `https://open.bigmodel.cn/api/paas/v4`
- **Stability**: Reliable from China, ~0.15-0.18s latency.
- **Models** (as of 2026-05): glm-4.5, glm-4.5-air, glm-4.6, glm-4.7, glm-5,
  glm-5-turbo, glm-5.1
- **Auth**: `$GLM_API_KEY` in Bearer header. Key is stored in `~/.hermes/.env`
  but may NOT be exported in the shell — extract with `grep GLM_API_KEY ~/.hermes/.env | cut -d= -f2`
- **Critical naming difference**: Z.ai uses names like `glm-4-flash`;
  智谱 direct has NO `glm-4-flash`. Use `glm-4.5-air` as the lightweight fallback.
  **Always verify models** with `GET /models` before configuring.
- **Config snippet**:
  ```yaml
  providers:
    zhipu:
      api_key: $GLM_API_KEY
      base_url: https://open.bigmodel.cn/api/paas/v4
  fallback_model:
    provider: zhipu
    model: glm-4.5-air
  ```
- **Verdict**: Best fallback for DeepSeek in China. Same API key as Z.ai,
  reliable endpoint, cheap lightweight model available.

## Latency Test Pattern

Quick diagnosis of intermittent API failures — 10-ping loop, no API key needed
for `/models` endpoint (returns 401 on valid auth attempt, which still proves
connectivity):

```bash
for i in $(seq 1 10); do
  result=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" --connect-timeout 5 \
    -H "Authorization: Bearer $KEY" https://<endpoint>/v1/models 2>&1)
  echo "attempt $i: $result"
  sleep 0.5
done
```

- `000` = connection timeout (5s limit hit) — endpoint unreachable
- `401` = connected, auth failed — reachable
- >1s response time = network congestion

## Cross-Provider Fallback Rule

Same-provider fallback (deepseek-v4-pro → deepseek-v4-flash) is **useless**
when the provider itself has network issues. Always use a **different provider**
for `fallback_model`. The whole chain must span at least 2 independent
infrastructures.

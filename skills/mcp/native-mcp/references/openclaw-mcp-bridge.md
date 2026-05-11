# OpenClaw MCP Bridge — Hermes Agent

Architecture: `Hermes ←── MCP/stdio ──→ openclaw-tools-mcp ←── HTTP :18789 ──→ OpenClaw Gateway`

The bridge exposes OpenClaw's browser/web_search/web_fetch tools as Hermes-native MCP tools. Useful when Hermes' built-in CDP browser hits walls (React events, stealth, persistent logins) and you want Playwright as an alternative execution engine.

## Pre-requisites

- Node.js ≥ 22
- OpenClaw installed globally: `npm install -g openclaw`
- OpenClaw Gateway running on localhost:18789

## Full Setup (from scratch)

### 1. Install OpenClaw (minimal — Gateway only, no messaging bridges)

```bash
npm install -g openclaw
mkdir -p ~/.openclaw

# Generate gateway token
openclaw doctor --generate-gateway-token

# Configure minimal
openclaw config set gateway.mode local
openclaw config set gateway.auth.mode token
openclaw config set gateway.bind loopback

# Start gateway (background)
OPENCLAW_NO_RESPAWN=1 openclaw gateway &
```

### 2. Get the gateway token

```python
import json
with open("/home/pebynn/.openclaw/openclaw.json") as f:
    cfg = json.load(f)
print(cfg["gateway"]["auth"]["token"])
```

### 3. Clone and build the MCP bridge

```bash
cd ~/tools
GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=true git clone https://github.com/haliphax-openclaw/openclaw-tools-mcp-server.git
cd openclaw-tools-mcp-server
npm install && npm run build
```

### 4. Create bridge config

`~/tools/openclaw-tools-mcp-server/openclaw-mcp.json`:
```json
{
  "gateway": {
    "url": "http://127.0.0.1:18789",
    "token": "<token from step 2>"
  },
  "tools": ["browser", "web_search", "web_fetch"]
}
```

### 5. Register in Hermes config

In `~/.hermes/config.yaml`, under `mcp_servers`:
```yaml
  openclaw-tools:
    command: node
    args:
      - /home/pebynn/tools/openclaw-tools-mcp-server/dist/index.js
    env:
      OPENCLAW_MCP_CONFIG: /home/pebynn/tools/openclaw-tools-mcp-server/openclaw-mcp.json
      OPENCLAW_MCP_TOOLS: "browser,web_search,web_fetch"
```

### 6. Reload

Restart Hermes gateway for MCP to pick up the new server. Tools appear as:
- `mcp_openclaw_browser` — 17 actions: navigate, snapshot, screenshot, click, type, scroll, select, hover, wait, evaluate, etc.
- `mcp_openclaw_web_search` — search engine with country/language/freshness filters
- `mcp_openclaw_web_fetch` — URL content extraction (markdown or text)

### 7. Smoke test

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | OPENCLAW_GATEWAY_TOKEN=<token> node ~/tools/openclaw-tools-mcp-server/dist/index.js
```

Should return 3 tools.

## Why OpenClaw browser vs Hermes built-in browser

| | Hermes CDP browser | OpenClaw Playwright browser |
|:--|:--|:--|
| Engine | Chrome DevTools Protocol | Playwright (Chromium) |
| React event handling | Limited (CDP dispatch) | `page.fill()` handles React synthesis |
| Stealth | Basic | Managed profiles + anti-detection |
| Session persistence | Per-session | Managed profiles with cookie persistence |
| Select/dropdown | Keyboard-based | `page.selectOption()` native |
| Cross-page sessions | No | Managed browser profile |

The key test: PDD SKU input box `fill()` — Hermes CDP's `browser_type` fails on React `onChange` synthesis. Playwright's `fill()` may succeed.

## Decision rule

If PDD SKU fill succeeds via OpenClaw browser → keep. If it still fails → the React/beast-core issue is deeper than browser engine choice → remove:

```bash
rm -rf ~/.openclaw ~/tools/openclaw-tools-mcp-server
# Remove openclaw-tools block from ~/.hermes/config.yaml mcp_servers
```

## Related

- OpenClaw tools reference: https://docs.openclaw.ai/tools/browser
- Bridge source: https://github.com/haliphax-openclaw/openclaw-tools-mcp-server
- Bridge docs: https://lobehub.com/mcp/haliphax-openclaw-tools-mcp-server

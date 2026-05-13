# Git Push Fallback via REST API

When `git push` fails (network blocked on port 443, timeout, proxy issues), use the GitHub REST API Git Database to push files directly. The MCP GitHub tools also work via REST under the hood.

## When to use

- `git push` times out on port 443
- MCP GitHub tools (`mcp_github_push_files`, `mcp_github_create_or_update_file`) work but hit payload limits for large files (>50KB)
- Need to push multiple files in a single commit

## Workaround: Git Database REST API

### Single commit with multiple files (upstream pattern)

```python
import subprocess, json, os, urllib.request

token = subprocess.check_output("echo $GITHUB_TOKEN", shell=True).decode().strip()
OWNER = "owner"
REPO = "repo"

def gh_req(method, path, data=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# Step 1: Get latest commit SHA on target branch
status, ref = gh_req("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
base_sha = ref["object"]["sha"]

# Step 2: Get base tree SHA
status, commit = gh_req("GET", f"/repos/{OWNER}/{REPO}/git/commits/{base_sha}")
base_tree = commit["tree"]["sha"]

# Step 3: Create blobs for each file
blobs = {}
for path, content in files.items():
    status, blob = gh_req("POST", f"/repos/{OWNER}/{REPO}/git/blobs", {
        "content": content,
        "encoding": "utf-8",
    })
    if status == 201:
        blobs[path] = blob["sha"]

# Step 4: Create tree (preserve existing files by using base_tree)
tree_items = [
    {"path": path, "mode": "100644", "type": "blob", "sha": sha}
    for path, sha in blobs.items()
]
status, tree = gh_req("POST", f"/repos/{OWNER}/{REPO}/git/trees", {
    "base_tree": base_tree,
    "tree": tree_items,
})
tree_sha = tree["sha"]

# Step 5: Create commit
status, new_commit = gh_req("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
    "message": "commit message",
    "tree": tree_sha,
    "parents": [base_sha],
})
commit_sha = new_commit["sha"]

# Step 6: Update ref (non-force)
status, result = gh_req("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main", {
    "sha": commit_sha,
    "force": False,
})
```

### MCP GitHub tools (smaller files)

For files under ~30KB, `mcp_github_create_or_update_file` works directly:
- Pass SHA of existing file to update
- For new files, omit SHA

`mcp_github_push_files` takes `{path, content}` array but has payload limits.

## Pitfalls

1. **File size**: REST API endpoints accept arbitrary size; MCP tools may have ~30-50KB payload limits
2. **Encoding**: Always use `"encoding": "utf-8"` for blobs — not base64
3. **Force push**: Set `"force": true` in step 6 if needed (rewrites history)
4. **base_tree is mandatory**: Creating a tree without `base_tree` replaces ALL files (deletes everything not in your tree_items)
5. **GITHUB_TOKEN**: Must be set in env; the `hermes-config` repo stores it in `~/.hermes/.env`

## Session Context (2026-05-13)

Used this pattern to push 5 dashboard review files (435KB total) to `pebynn/hermes-agent`:
- 2 small files (i18n en.ts 25KB + zh.ts 25KB) via `mcp_github_create_or_update_file`
- 3 large files (plugin_api.py 62KB + index.js 132KB + kanban_db.py 192KB) via REST API Git Database

Upstream PR flow: fork → push to fork → PR from fork to upstream.

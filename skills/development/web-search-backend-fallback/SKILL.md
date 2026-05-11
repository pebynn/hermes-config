---
allowed-tools:
- terminal
- file
- read_file
- patch
author: unknown
description: 配置 Hermes web 搜索后端多级备选链（Parallel → Tavily → Firecrawl）。修改 tools/web_tools.py
  使 web_search 在前端后端失败时自动切到下一个。
name: web-search-backend-fallback
trigger:
- web_search 报错，API key 过期或余额不足
- 想设置一个主/备搜索后端避免单点故障
- 新安装了一个搜索后端（Parallel/Firecrawl/Exa）要加入备选链
version: 1.0.0
when-to-use: '当 web_search 工具返回 401（key过期）、余额不足（insufficient credit）、

  或网络错误时，需要配置备选后端避免搜索完全不可用。

  也适用于刚安装新搜索后端想加入自动备选链的场景。'
---

# Hermes Web 搜索后端备选链

## 解决的问题

Hermes 原生只支持**单个** web 搜索后端。如果该后端 key 过期、余额不足或网络不通，web_search 直接报错没有兜底。

这个改动让 web_search 尝试当前后端失败后自动切换下一个，实现热备选。

## 当前配置

```
主选: Parallel CLI（API key 已配）
备选: Tavily（API key 已配，免费500次/月）
末选: Firecrawl（默认）
```

备选链定义在 `web_tools.py` 的 `fallback_chain` 字典里。

## 源码改动

文件: `~/.hermes/hermes-agent/tools/web_tools.py`

将 `web_search_tool()` 的 `# Dispatch to the configured backend` 段落改为带 fallback 循环的版本：

```python
# Dispatch to the configured backend with fallback chain
backend = _get_backend()
fallback_chain = {"parallel": "tavily", "tavily": None, "exa": None}
tried = set()

while backend and backend not in tried:
    tried.add(backend)
    try:
        if backend == "parallel":
            response_data = _parallel_search(query, limit)
        elif backend == "exa":
            response_data = _exa_search(query, limit)
        elif backend == "tavily":
            raw = _tavily_request("search", {
                "query": query, "max_results": min(limit, 20),
                "include_raw_content": False, "include_images": False,
            })
            response_data = _normalize_tavily_search_results(raw)
        else:
            # firecrawl default
            response = _get_firecrawl_client().search(query=query, limit=limit)
            response_data = {"success": True, "data": {"web": _extract_web_search_results(response)}}

        # (确认结果格式后 return)
        ...

    except Exception as e:
        logger.warning("Backend '%s' failed: %s — trying fallback", backend, str(e)[:60])
        backend = fallback_chain.get(backend)

# All backends exhausted
error_msg = f"All search backends failed (tried: {', '.join(sorted(tried))})"
return tool_error(error_msg)
```

## 配置方法

### 1. 安装搜索后端

| 后端 | 安装 | 环境变量 |
|:-----|:-----|:--------|
| Parallel CLI | `pip install "parallel-web-tools[cli]" --break-system-packages` | `PARALLEL_API_KEY` |
| Tavily | 内置（需API key） | `TAVILY_API_KEY` |
| Exa | 内置（需API key） | `EXA_API_KEY` |
| Firecrawl | 内置（需API key或tool gateway） | `FIRECRAWL_API_KEY` |

### 2. 写 API key 到 .env

```bash
echo "PARALLEL_API_KEY=t-your-key" >> ~/.hermes/.env
```

### 3. 切换 config.yaml

```yaml
web:
  backend: parallel   # 主选，失败自动切备选
```

### 4. 维护 fallback_chain

新增后端或调整优先级时，改 web_tools.py 里的 `fallback_chain` 字典：

```python
# key=当前后端, value=失败后切到哪个
# None 表示没有备选（直接报错）
fallback_chain = {
    "parallel": "tavily",   # parallel 失败 → 切 tavily
    "tavily": None,         # tavily 失败 → 没有备选（报错）
    "exa": "tavily",        # exa 失败 → 切 tavily
}
```

### 5. 重启会话

`_get_backend()` 读 config.yaml 的缓存值，改完 `web.backend` 后需要新会话生效。API key 写入 `.env` 后同样需要重启。

## 验证

```bash
# 测试 Parallel
set -a; source ~/.hermes/.env; set +a
parallel-cli search "test" --json

# 测试 Tavily
curl -s -w '\nHTTP:%{http_code}' "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\":\"$TAVILY_API_KEY\",\"query\":\"test\",\"max_results\":1}"
```

也可以派一个 delegate_task 带 `toolsets=["web"]` 实际调用 web_search 验证备选链生效。

## 已知坑点

- **源码改动会被 Hermes 更新覆盖** — 每次升级 Hermes 后需要重新 patch `web_tools.py`
- **环境变量只读一次** — Hermes 进程启动时读取 .env，中途改 .env 不生效，需要重启进程
- **Parallel CLI 需要余额** — key 认证通过但余额不足时会报 `Insufficient credit`，自动切到备选
- **web.backend 不在白名单时** — `_get_backend()` 会走自动检测逻辑，选第一个有 env var 的后端

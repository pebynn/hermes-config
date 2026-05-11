# 中国网络环境下的外源技能安装

## 问题
`git clone https://github.com/...` 在中国大陆网络环境下频繁失败：
- GnuTLS recv error (-110): TLS connection non-properly terminated
- 超时 (120s+)

## 解决方案：raw.githubusercontent.com 直取

GitHub 的 raw 内容 CDN 在中国通常可达（curl 可达即使 git clone 不可达）：

```bash
BASE="https://raw.githubusercontent.com/{owner}/{repo}/{ref}"
curl -sL --connect-timeout 10 "$BASE/path/to/file" -o local_path
# 必须带 User-Agent header
```

**批量下载模式**（Python）：
```python
import urllib.request
url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
with urllib.request.urlopen(req, timeout=30) as resp:
    content = resp.read()
```

## 获取目录清单
用 GitHub API 替代 `git ls-tree`：
```
GET https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}
```
返回 JSON 数组，每项含 `download_url` 字段指向 raw 地址。

## 安装流程
1. GitHub API → 获取目录清单
2. raw.githubusercontent.com → 逐个下载文件
3. `py_compile.compile()` → 验证 Python 脚本语法
4. `skill-security-auditor` → 安全审计

## 已知限制
- 大文件（>1MB）raw 下载可能超时
- GitHub API 有速率限制（未认证 60 req/h）
- 此模式不能替代 `git clone` 用于需要 `.git` 历史的场景

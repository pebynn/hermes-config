# Hindsight 部署与故障排查

Hindsight (v0.5.5) 是 Agent Memory 服务，提供向量化会话记忆和知识检索。Docker 部署。

## docker-compose.yml 模板

```yaml
version: "3.8"
services:
  hindsight:
    image: ghcr.io/vectorize-io/hindsight:latest
    container_name: hindsight
    restart: always
    ports:
      - "8888:8888"
      - "9999:9999"
    environment:
      HINDSIGHT_API_LLM_PROVIDER: openai
      HINDSIGHT_API_LLM_API_KEY: sk-xxx
      HINDSIGHT_API_LLM_BASE_URL: https://api.deepseek.com/v1
      HINDSIGHT_API_LLM_MODEL: deepseek-v4-flash
      HINDSIGHT_API_PORT: 8888
      HINDSIGHT_UI_PORT: 9999
      HINDSIGHT_CORS_ENABLED: "true"
      HF_ENDPOINT: https://hf-mirror.com    # ← 国内必须
    volumes:
      - ./hindsight_data:/home/hindsight/.pg0
```

## 中国网络特殊配置

### HuggingFace 镜像（必须）

hindsight 启动时下载两个模型：
- `BAAI/bge-small-en-v1.5` (embeddings, 384-dim)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (reranker)

国内直连 HF 不通 → 必须设 `HF_ENDPOINT: https://hf-mirror.com`，否则启动永久卡住。

### 模型下载超时

模型约 60-90MB，hf-mirror 下载 20-30 秒。完整启动时间约 60-90 秒（含 PG 初始化 + LLM 验证 + 模型加载）。

## 常见故障

### 1. PostgreSQL 权限错误

```
RuntimeError: Failed to start embedded PostgreSQL after 5 attempts.
Last error: IO error: Permission denied (os error 13)
```

**原因**：`hindsight_data/` 目录属主为 root（上次 `docker compose up` 可能用 sudo 运行过）。

**修复**：
```bash
docker stop hindsight && docker rm hindsight
sudo rm -rf hindsight_data
mkdir -p hindsight_data
docker compose up -d
```

不要用 chmod 777，直接删目录让 Docker 用正确权限重建最干净。

### 2. 启动后 /health 无响应

启动日志显示 `Waiting for application startup` 但未完成：
- 检查日志 `docker logs hindsight | grep -i error`
- 模型下载卡住 → 检查 HF_ENDPOINT
- PG 权限问题 → 见 §1

### 3. 端口冲突

8888 (API) 和 9999 (UI) 必须都空闲。`ss -tlnp | grep -E '8888|9999'` 检查。

## 验证命令

```bash
# 容器状态
docker ps --filter name=hindsight

# 健康检查
curl -s http://localhost:8888/health
# 预期: {"status":"healthy","database":"connected"}

# 启动日志（关键行）
docker logs hindsight | grep -E 'startup|error|Embeddings|Reranker|PostgreSQL'
```

## 开机自启

`restart: always` 已处理崩溃重启。Docker 本身需开机自启：
```bash
sudo systemctl enable docker
```

可选 systemd 服务（推荐但非必须）：
```ini
[Unit]
Description=Hindsight Agent Memory
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pebynn/tools/hindsight
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=pebynn

[Install]
WantedBy=multi-user.target
```

## 知识管道定位

hindsight 在 memory → hindsight → gbrain → graphify → wiki 管道中的角色：
- 接收 session 对话记录
- 向量化存储
- 提供语义检索（区别于 memory 的精确匹配）

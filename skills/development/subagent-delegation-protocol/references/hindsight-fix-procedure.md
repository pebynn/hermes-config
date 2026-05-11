# Hindsight 修复程序

2026-05-11 实际修复记录

## 症状

```
hindsight_retain → 'HindsightEmbedded' object has no attribute 'aretain'
hindsight_recall → 'HindsightEmbedded' object has no attribute 'arecall'
hindsight-embed.log → Daemon startup failed: No module named 'hindsight_embed'
```

## 根因

三层故障：
1. `hindsight_embed` Python包未安装
2. 兼容shim (`hindsight_shim.py`) 只有同步方法(retain/recall)，缺少Hermes插件需要的异步方法(aretain/arecall/areflect/aretain_batch)
3. config.yaml中 `endpoint: http://localhost:8888/v1` 路径错误（应为 `http://localhost:8888`）

## 修复步骤

### 1. 安装依赖

```bash
cd /home/pebynn/tools/hindsight
bash ensure_hindsight.sh
# 实际执行: pip install hindsight-embed hindsight-client
# 验证: python3 -c "import hindsight_embed; print('OK')"
```

### 2. 更新兼容shim

`~/tools/hindsight/hindsight_shim.py` 需要添加异步方法：

```python
async def aretain(self, content, metadata=None, context=None, 
                  timestamp=None, document_id=None, tags=None):
    return await self._client.aretain(self._bank_id, content, ...)

async def arecall(self, query, limit=5, ...):
    return await self._client.arecall(self._bank_id, query, ...)

async def areflect(self, query, budget="low", context=None):
    return await self._client.areflect(self._bank_id, query, ...)

async def aretain_batch(self, items, document_id=None, document_tags=None):
    return await self._client.aretain_batch(self._bank_id, items, ...)
```

### 3. 复制shim到Hermes venv

```bash
cp ~/tools/hindsight/hindsight_shim.py \
   ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hindsight.py
```

### 4. 修正config.yaml端点

```yaml
# 前: endpoint: http://localhost:8888/v1
# 后: endpoint: http://localhost:8888
```

### 5. 验证

```bash
# Docker容器运行确认
curl http://localhost:8888/health
# → {"status":"healthy","database":"connected"}

# 功能验证
python3 -c "
from hindsight_client import Hindsight
# aretain → arecall → areflect 全链路
"
```

### 6. 重启Hermes

shim在会话启动时加载。修复后必须重启Hermes才能使hindsight_retain/recall/reflect MCP工具生效。

## 基础设施确认

- Docker: `ghcr.io/vectorize-io/hindsight:latest` 运行在端口8888
- PostgreSQL: 容器内PostgreSQL存储向量数据
- Bank: 默认使用 "hermes" bank
- API key: config.yaml中 `api_key: $DEEPSEEK_API_KEY`（embedding用flash模型）

## Hindsight在kanban架构中的用途

- **kanban_create前**: hindsight_recall(任务关键词) → 语义搜索历史经验 → 注入到kanban body
- **kanban_complete后**: 提取metadata.lessons_learned → hindsight_retain(教训)
- **跨会话恢复**: hindsight_reflect("当前kanban任务进度") → 综合所有记忆 → 恢复上下文

与memory工具的互补：
- memory: 4000字符限制，快速键值存储，用于关键事实
- hindsight: 无容量限制，语义向量搜索，用于长期教训和跨域关联

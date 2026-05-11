# 内置压缩引擎 tool_calls 孤儿 Bug 诊断记录

## 发现时间
2026-04-30 21:52

## 错误现象

DeepSeek API 连续返回 400 错误（会话 `20260430_144500_81ee0f`）：
```
Error code: 400 - {'error': {'message': "An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. (insufficient tool messages following tool_calls message)"}}
```

累计发生 6 次（21:52:03 → 21:54:57），非偶发。标记为 `Non-retryable client error`，说明 Hermes 不自动重试此错误类型。

## 根因定位

Hermes 内置压缩引擎（`compression.enabled: true` + `context.engine: compressor`）的压缩逻辑：
1. 扫描历史消息
2. 删除/摘要化的 tool 返回结果（role=tool 的消息）
3. **但保留了 assistant 消息中的 tool_calls 数组**（含 tool_call_id）

当重构后的对话历史发送到 DeepSeek API 时，存在 tool_call_id 对应的 tool 角色消息缺失。DeepSeek API 校验通过，拒绝请求。

## 修复

```yaml
# ~/.hermes/config.yaml
compression:
  enabled: false    # 关闭压缩
  protect_last_n: 50  # 保留作为备用阈值
```

## 验证

- 改配置后 `/new` 重建会话，API 调用恢复正常
- 压缩关闭后对 cost 的影响：低成本 flash 模型 + 120 max_turns 上限，正常使用不会超限

## 关联

- Hermes 内置压缩引擎(`compressor`) 与 context-compression-protocol skill 描述的手动压缩协议是两套机制
- 内置引擎有 bug，不可用
- 手动协议仍是有效的上下文管理方法，但不依赖内置引擎
- DeepSeek API 的 strict 校验（检查 tool_calls ↔ tool_response 配对）优于 Azure/OpenAI 的实现，后者对 orphan tool_calls 容忍度更高

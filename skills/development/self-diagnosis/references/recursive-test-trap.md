# 递归测试陷阱 (Recursive Test Fork Bomb)

## 故障模式

当审计/测试脚本和其测试文件形成递归调用时，会触发进程 fork bomb：

```
audit_bd_layer.py → check_pytest_integration() → subprocess.run(pytest test_audit_bd_layer.py)
  ↓
test_audit_bd_layer.py → from audit_bd_layer import run_extended_audit
  ↓
run_extended_audit() → check_pytest_integration() → subprocess.run(pytest...)
  ↓
(100+ 进程死锁，CPU/RAM耗尽)
```

## 识别信号

- `ps aux | grep pytest | wc -l` → 持续增长，超过100+
- 子进程内存递减（PID小→RES大，PID大→RES小，末级125% CPU）
- subprocess timeout 无效（每个子进程独立计时）
- `audit_bd_layer.py --extended` 永无输出

## 修复模式

```python
# ❌ 错误: 只排除一个测试，另一个仍触发递归
["-k", "not test_extended_audit_runs_all_guardrails"]

# ✅ 正确: 排除所有调用 run_extended_audit 的测试
["-k", "not (test_extended_audit_runs_all_guardrails or test_extended_audit_semantic_skipped_by_default)"]
```

## 预防规则

1. 测试文件中**凡是导入并调用被测脚本的顶层函数**（如 `run_extended_audit`），都必须从 `-k` 过滤器排除
2. 不依赖单一的测试名排除——检查被测脚本的函数调用链，确认所有路径
3. timeout 设 600s（不是 180s），因排除后的合法测试仍可能耗时

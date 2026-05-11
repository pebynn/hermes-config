# Code-Domain Lessons — 编码教训

## 🔴 CRITICAL

### 纯文本规则不可靠，行为约束必须前置到速查表
- SOUL.md 中的文本规则（如 [1.5] lesson_inject），主代理可能会跳过不执行
- 解决方案：在调度模式速查表中把步骤作为前缀写入每条路径
- 不要依赖独立段落描述 — 必须嵌入到每条操作路径中
- **纠正次数**: 1
- **首次发现**: 2026-05-07

### 缓存文件路径前缀验证（_cache_get 的 k_ 陷阱）
- `_cache_get(FIN_CACHE_DIR, sym)` 强制在文件名前加 `k_` 前缀 → 比如 `k_000001.parquet`
- 但实际财务缓存文件存储为 `~/.finquant/cache/financial/{code}.parquet`（无 `k_` 前缀）
- 每次调用 `_cache_get` 都因文件名不匹配而缓存未命中，导致重复调用 AKShare
- **修复**: 直接使用 `pd.read_parquet(FIN_CACHE_DIR / f"{sym}.parquet")`，跳过 `_cache_get`
- **事故**: 3041 只候选股全量重新拉取 AKShare 数据，导致 >300s 超时
- **纠正次数**: 1
- **来源**: 20260430_011333_a909bb

## 🟠 HIGH

### Python 脚本产出必须验证语法
- 每次产出 .py 后立即: `python3 -c "import py_compile; py_compile.compile('script.py', doraise=True)"`
- 常见 bug: async with 缩进错误导致 context 提前关闭
- stealth-browser-automation 技能已记录完整诊断方法

### 渲染/可视化改动必须实际生成确认
- 不能仅代码检查 → 实际运行 → 检查产出文件
- 图表生成类必须打开图片确认内容正确

### 用户不想要推命令
- 不要向用户推任何 shell 命令语法
- 内部调度完成，只汇报结果
- 用户不需要学任何命令格式

### 财务数据缓存优先策略
- 检查本地 parquet 缓存 → 缓存存在且数据新鲜 → 直接返回
- 仅当缓存缺失或数据陈旧时才调用 AKShare API
- 关键代码:
  ```python
  cache_path = FIN_CACHE_DIR / f"{sym}.parquet"
  if cache_path.exists():
      df = pd.read_parquet(cache_path)
      # 解析 ROI/EPS 等因子
      return parsed_values
  # 仅兜底: ak.stock_financial_abstract_ths(sym)
  ```
- **效果**: TOP 30 分析从 >300s（超时）降至 84 秒，财务数据 0 额外 API 调用
- **来源**: 20260430_011333_a909bb

## 🟡 MEDIUM

### 零成本工具链
- uv 0.11.8 (~/.local/bin/uv)
- ruff 0.15.12 (uv tool install)
- pre-commit 4.6.0
- Crawl4AI latest
- pip 加清华镜像: -i https://pypi.tuna.tsinghua.edu.cn/simple

### 技能/资源命名约定
- 使用下划线 `_` 而不是连字符 `-`
- ✅ `financial_analysis_automation` ✓
- ❌ `financial-analysis-automation` ✗
- 连字符可能导致导入路径解析问题
- **纠正次数**: 1
- **来源**: 20260429_183418_9a881f

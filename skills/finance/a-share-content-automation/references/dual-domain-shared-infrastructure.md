# 双域共享基础设施模式

> 记录：2026-05-07 雪球数据源从 writing-domain 独占到 writing/finance 双域共享

## 问题

`xueqiu_kline.py` 最初创建在 `~/.hermes/profiles/writing-domain/skills/a-share-data-collector/scripts/`，仅供 writing-domain 使用。但 finance-domain 同样需要晚间K线数据（19:00-08:00 AKShare push2 黑窗），且雪球cookie是全局共享的。

## 方案

1. **主副本** → `~/quant/xueqiu_kline.py`（双域共享位置）
2. **原位置** → symlink 到 `~/quant/xueqiu_kline.py`（保持 writing-domain 原有 import 路径不变）
3. **finance-domain** → 通过 `kline_fallback.py` wrapper 访问（晚间降级专用）

## 关键设计

```python
# 各域通过统一接口访问
# writing-domain: import from ~/quant/ directly
import sys; sys.path.insert(0, str(Path.home()/"quant"))
from xueqiu_kline import XueqiuSource

# finance-domain: 通过 kline_fallback wrapper
from kline_fallback import get_stock_kline, get_indices_snapshot
```

## 适用场景

任何双域共同依赖的模块都应该放 `~/quant/`：
- 数据源（K线、行情、财务）
- 公用工具（校验、交叉验证）
- 信号引擎共享模块

不适用：域专属逻辑（writing的发布管线、finance的回测框架）留在各自 profiles。

## 注意事项

- 模块迁移后必须验证 import 在双域都正常
- 原位置保留 symlink，避免破坏现有引用
- 模块内的路径引用用绝对路径或 `Path.home()`
- 新增共享模块时更新双域 SOUL.md

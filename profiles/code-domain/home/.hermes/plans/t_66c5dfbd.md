# R11-B Strategy Reversal 优化实施计划

> Task: t_66c5dfbd | 2026-05-13 | code-domain

## 设计方案

### 当前状态 (R10-B)
```
MOM_20D_MIN = 0.08        (强动量门, R9=5%, R10收紧至8%)
SECTOR_MAX_POSITIONS = 2   (行业上限, R10新增)
ATR_STOP_MULT = 1.5        (仅作布尔门, 未参与实际sizing计算)
MAX_POSITIONS = 8          (R9/R10一致)
```

R10回测: ann=8.96%, win=50.2%, sharpe=2.601, MDD=-2.40%
R9回测: ann=18.1% (来自memory), MDD=-14.89%

### R11 修改方案

| 参数 | R10值 | R11目标 | 理由 |
|:---|:---|:---|:---|
| MOM_20D_MIN | 0.08 | 0.06 | R10过紧(8%)排除大量有效反转候选 → 折中(R9=5%, R10=8%) |
| SECTOR_MAX_POSITIONS | 2 | 3 | R10=2过度限制分散化 → 放宽至3(R9无限制) |
| ATR_STOP_MULT | 1.5(仅门控) | 2.0(写入sizing逻辑) | 将ATR_STOP_MULT从布尔门改为实际sizing上限, 解除硬编码2.0 |
| MAX_POSITIONS | 8 | 8 | 保持不变(R9/R10均验证) |

### 保留R10优秀项（不做修改）
- STOP_LOSS = -0.08
- TRAILING_STOP_PCT = -0.04
- TP1_HALF_PCT = 0.10
- TP2_FULL_PCT = 0.22
- CANDLE_CONFIRM = False
- SECTOR_HEAT_HARD_FILTER = 0.65
- FUNDAMENTAL_FILTER_ENABLED = True
- VOLUME_CONFIRM_ENABLED = True
- MARKET_TIMING_ENABLED = True (ma_cross)
- ENTRY_DELAY = True
- DECLINE_WEIGHT = 0.35, RSI_WEIGHT = 0.25, VOL_WEIGHT = 0.20, MOM_WEIGHT = 0.20
- REBALANCE_DAYS = 3
- HOLD_WINNERS = True

### 代码修改细节

**Change 1: MOM_20D_MIN (第115行)**
```
- MOM_20D_MIN = 0.08                # R10
+ MOM_20D_MIN = 0.06                # R11: 折中R9(5%)与R10(8%), 恢复候选池广度
```

**Change 2: SECTOR_MAX_POSITIONS (第111行)**
```
- SECTOR_MAX_POSITIONS = 2          # R10
+ SECTOR_MAX_POSITIONS = 3          # R11: 放宽行业集中度限制
```

**Change 3: ATR_STOP_MULT + execute_entry逻辑 (第99行 + 第696行)**
```
- ATR_STOP_MULT = 1.5               # R10: enabled ATR position sizing (was 0.0 disabled)
+ ATR_STOP_MULT = 2.0               # R11: 调高multiplier至2.0x, 写入sizing逻辑作为实际上限
```
`execute_entry` 第696行:
```
- risk_scalar = min(target_risk_pct / atr_pct, 2.0)  # cap at 2x
+ risk_scalar = min(target_risk_pct / atr_pct, ATR_STOP_MULT)
```

**Change 4: 文档字符串 + docstring更新 (第1-12行)**
将 R10-B 标题改为 R11-B, 增加R11变更说明。

### 替代方案

1. **MOM_20D_MIN回退至5%(R9)**: 风险在于可能引入过多弱动量信号, 虽然R9 ann=18.1%但MDD=-14.89%不可接受 → 选择折中6%
2. **SECTOR_MAX_POSITIONS完全移除(R9)**: 会失去R10的行业集中度保护 → 选择放宽至3
3. **禁用ATR sizing(设ATR_STOP_MULT=0)**: 丢失R10新增的风险管理能力 → 保留但强化
4. **同时调整STOP_LOSS**: R10的-8%配合低MDD表现良好, 暂不修改 → 保留

### 风险

1. MOM_20D_MIN 6%可能仍不够宽 → 若R11结果仍远低于R9(18.1%), 建议R12回退至5%
2. SECTOR_MAX_POSITIONS=3 → 同一行业最多3只, 若某行业集中崩盘, MDD可能上升
3. ATR sizing的target_risk_pct=0.015未变, 仅改了cap → 对大多数正常ATR股票无影响, 仅对极端高波动股票放大了头寸

## 实施计划

### 第2步产物
- [x] plan文件: ~/.hermes/plans/t_66c5dfbd.md

### 第3步: TDD
- 创建 test_r11b_tdd.py: 验证4项参数变更 + 铁律保持 + 回归防护

### 第4步: 编码
- strategy_reversal.py: 第1-12行(docstring), 第99行(ATR_STOP_MULT), 第111行(SECTOR_MAX), 第115行(MOM_20D_MIN), 第696行(risk_scalar cap)
- round11_B_config.json: 新配置摘要JSON

### 第5步: 调试
- 运行TDD测试确认全部GREEN
- Python语法检查

### 第6步: 自审
- 逐项核对R11变更点
- 确认未修改铁律 (LEVERAGE=1.0, 无未来函数, 数据双源)
- 确认仅修改 evo_optimizer/ 下文件

### 第7步: 验证
- 运行 pytest test_r11b_tdd.py
- 验证 round11_B_config.json 格式正确

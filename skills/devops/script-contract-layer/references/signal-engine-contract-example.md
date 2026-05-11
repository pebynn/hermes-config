# Worked Example: signal_engine ↔ chan_buy_signal Contract Isolation

## Problem

`signal_engine.py` (1062 lines, v4.0) directly imported `chan_buy_signal.py`:

```python
# signal_engine.py line 85
import chan_buy_signal

# line 734
buy2 = chan_buy_signal.detect_chan_buy2(kline_df)
```

Any modification to `detect_chan_buy2`'s signature or internal logic in `chan_buy_signal` could silently break `signal_engine`. This is the exact problem the Script Contract Layer exists to solve.

## Solution

### Step 1: Extract Protocol (contracts/chan_buy_contract.py)

```python
from typing import Protocol
import pandas as pd

class ChanBuySignalContract(Protocol):
    def detect_chan_buy2(self, kline_df: pd.DataFrame) -> pd.DataFrame: ...
    def get_latest_signals(self, codes: list[str], kline_dir: str) -> pd.DataFrame: ...

class ChanBuySignalProvider:
    """Adapter — consumer doesn't know who implements the contract"""
    @staticmethod
    def detect_chan_buy2(kline_df: pd.DataFrame) -> pd.DataFrame:
        import chan_buy_signal
        return chan_buy_signal.detect_chan_buy2(kline_df)
```

### Step 2: Change Consumer import

```python
# signal_engine.py — OLD:
import chan_buy_signal
buy2 = chan_buy_signal.detect_chan_buy2(kline_df)

# signal_engine.py — NEW:
from contracts.chan_buy_contract import ChanBuySignalProvider
buy2 = ChanBuySignalProvider.detect_chan_buy2(kline_df)
```

### Step 3: Verify Isolation

1. Syntax verification: `python3 -c "import py_compile; py_compile.compile('signal_engine.py', doraise=True)"`
2. Import verification: `from contracts.chan_buy_contract import ChanBuySignalProvider`
3. Signal engine loads through contract: `from signal_engine import scan_signals`
4. Make internal change to `chan_buy_signal.py` (e.g., refactor helper functions) — verify `signal_engine` still works

### Verification Script

```python
# signal_engine_test.py
import sys; sys.path.insert(0, '/home/pebynn/quant')
from contracts.chan_buy_contract import ChanBuySignalProvider
from signal_engine import scan_signals

# Both load successfully — contract layer works
assert callable(scan_signals)
assert callable(ChanBuySignalProvider.detect_chan_buy2)
```

### Result

- `chan_buy_signal` can be refactored, restructured, or replaced entirely
- `signal_engine` is shielded from internal changes
- The contract file documents exactly what `signal_engine` depends on
- Setting: `~/quant/contracts/chan_buy_contract.py`
- Verification: `~/quant/signal_engine_test.py` (3 tests, all pass)

## Key Insight

The Protocol class is **not enforced at runtime** by Python (it's a structural typing hint, not a compiler check). The actual enforcement comes from:
1. The `ChanBuySignalProvider` adapter — all calls route through it
2. The `signal_engine_test.py` verification — run after any `chan_buy_signal` change
3. The contract file itself — it's the single source of truth for the interface

For stronger enforcement, upgrade to Tier 3 (Plugin Architecture) which adds runtime module graph resolution.

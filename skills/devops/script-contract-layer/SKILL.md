---
name: script-contract-layer
description: Script-to-script contract enforcement -- explicit dependency declarations, Protocol-based interface isolation, cross-script drift prevention. Java JPMS/OSGi concepts mapped to Python script governance.
domain: ops-domain
version: 1.0.0
trigger:
- recurring bugs caused by script A modifying behavior expected by script B
- scripts that get modified multiple times and lose original logic boundaries
- cross-script interface drift (function signature changes that silently break consumers)
- modification of script A breaks script B unexpectedly
- user asks about modularization, module governance, or interface contracts
related_skills:
- data-accuracy-layer
---

# Script Contract Layer -- Governance for Script-to-Script Interaction

## Why This Skill Exists

Hermes has many Python scripts across domains (writing/quant/ec/ops). The dominant failure pattern:

Script A gets modified N times. Each modification makes sense in isolation. Over time, A's interface (function signatures, return shapes, side effects) drifts. Script B, which imports A, silently starts producing wrong output. Nobody notices until the pipeline generates bad data.

Previous fixes targeted symptoms (fix B when it breaks). This skill targets structure: treat each script as a module with an explicit contract.

## Conceptual Foundation: Java JPMS to Python

| JPMS Concept | Python Equivalent | What It Solves |
|---|---|---|
| module-info.java | domain.yaml per script cluster | One declaration to rule all dependencies |
| requires | depends_on | Know who depends on whom, detect broken links |
| exports | all + Protocol interface | Only the declared interface is public |
| exports ... to | visible_to decorator | Granular visibility, not global open |
| provides/uses | ScriptRegistry pattern | Consumers dont import, they request |
| Module graph resolution | validate-deps startup check | Fail-fast, dont run with broken contracts |
| Strong encapsulation | private conventions + proxy layer | Internal refactors cant leak to consumers |
| Semantic versioning | __interface_version__ | Breaking changes are explicit, not silent |
| OSGi bundle lifecycle | Plugin directory with metadata | Hot-reloadable script components |

## Three-Tier Implementation

### Tier 1: Lightweight -- Metadata + Validation

Zero code changes. Add metadata and a scanner.

**Step 1:** Create domain.yaml per script cluster:

```yaml
# writing-data/hermes-domain.yaml
domain: writing
version: 1.0.0
scripts:
  morning_brief.py:
    version: 2.1.0
    exports: [fetch_data, format_brief]
    depends_on: [data_common, data_guard]
    internal: [_parse_warnings, _build_sections]
  data_common.py:
    version: 1.3.0
    exports: [safe_float, load_all_data]
    depends_on: []
```

```yaml
# quant/hermes-domain.yaml
domain: quant
version: 1.0.0
scripts:
  signal_engine.py:
    version: 4.0.0
    exports: [scan_signals, today_signal]
    depends_on: [chan_buy_signal, stock_fund_flow, data_common]
  chan_buy_signal.py:
    version: 2.0.0
    exports: [detect_chan_buy2, get_latest_signals]
    depends_on: [data_common]
```

**Step 2:** Add __interface_version__ to every script:

```python
# At the top of each script file
__interface_version__ = "2.1.0"
"""
CHANGELOG:
2.1.0 - 2026-05-08: scan_signals now returns DataFrame with sector column added
2.0.0 - 2026-05-01: BREAKING - scan_signals signature changed (removed market param)
1.0.0 - 2026-04-15: Initial
"""
```

**Step 3:** Implement validate-deps scanner (see scripts/validate_deps.py):

Validates:
1. Every import in each script matches its depends_on declaration
2. Every function called from another script is in that script's exports
3. No circular dependencies
4. __interface_version__ exists on every script
5. Orphan imports (script imports something not in any domain.yaml)

**Step 4:** Run as pre-commit hook + cron.

**Effort: 1-2 days | Risk: none (metadata only) | Effect: catches silent dependency introduction**

### Tier 2: Medium -- Protocol Contract Layer

Add a contracts/ directory with Python Protocol definitions. Scripts interact through these, not direct import.

```python
# quant/contracts/signal_contracts.py
from typing import Protocol
from pandas import DataFrame

class ChanBuySignalContract(Protocol):
    def detect_chan_buy2(kline_df: DataFrame) -> DataFrame: ...
    def get_latest_signals(codes: list, kline_dir: str) -> DataFrame: ...

class SignalEngineContract(Protocol):
    def scan_signals(market: str, mc_min: float, mc_max: float) -> DataFrame: ...
    def today_signal() -> DataFrame: ...
```

Consumer pattern -- don't import directly, request through registry:

```python
# OLD (direct import):
from chan_buy_signal import detect_chan_buy2

# NEW (contract-mediated):
from contracts import ChanBuySignalContract
from registry import get_implementation

chan_buy = get_implementation(ChanBuySignalContract)
signals = chan_buy.detect_chan_buy2(kline_df)
```

Interface drift detector:

```python
def detect_interface_drift(script_path: str, contract_path: str) -> list:
    """Compare actual function signatures vs contract definitions.
    Returns list of mismatches. Run in CI or pre-commit."""
    # Uses inspect.signature() vs parsed contract signatures
    # Any mismatch becomes a report
```

**Effort: 3-5 days | Risk: medium (modifies import paths) | Effect: interface changes auto-detected, consumers isolated**

### Tier 3: Heavy -- Full Plugin Architecture

Each script becomes a plugin with descriptor file + registry-based resolution, modeled after JPMS + OSGi.

Structure:

```
quant/
  plugins/
    signal_engine/
      plugin.yaml        # module descriptor
      __init__.py
      core.py            # original logic
    chan_buy_signal/
      plugin.yaml
      __init__.py
      core.py
    stock_fund_flow/
      plugin.yaml
      __init__.py
      core.py
  contracts/
    signal_contracts.py  # Protocol definitions
  registry.py            # ScriptRegistry (OSGi ServiceRegistry simplified)
  runner.py              # Module graph resolution + lifecycle
```

plugin.yaml (JPMS module-info.java inspired):

```yaml
# plugins/signal_engine/plugin.yaml
module: signal_engine
version: 4.0.0
provides:
  - interface: contracts.SignalEngineContract
    implementation: core.SignalEngine
requires:
  - module: chan_buy_signal
    version: ">=2.0.0,<3.0.0"
    contract: contracts.ChanBuySignalContract
  - module: stock_fund_flow
    version: ">=1.0.0"
    contract: contracts.StockFundFlowContract
exports:
  - scan_signals
  - today_signal
internal:
  - _compute_l1_factors
  - _merge_layers
```

ScriptRegistry:

```python
class ScriptRegistry:
    _providers: dict = {}

    @classmethod
    def register(cls, contract, plugin, version):
        cls._providers[contract] = (plugin, version)

    @classmethod
    def resolve(cls, contract, version_constraint="*"):
        plugin, version = cls._providers.get(contract)
        if not _satisfies(version, version_constraint):
            raise ModuleResolutionError(...)
        return plugin

    @classmethod
    def validate_graph(cls):
        """JPMS module graph resolution:
        1. Scan all plugin.yaml files
        2. Build dependency graph
        3. Check all requires have matching provides
        4. Detect cycles
        5. Fail-fast on any missing or conflicting dependency"""
```

Startup flow (runner.py):
1. Scan plugins/ directory, read all plugin.yaml
2. Build dependency graph (JPMS module graph style)
3. Validate: all requires satisfied, no cycles, versions compatible
4. Load plugins in topological order, register in ScriptRegistry
5. Missing or conflicting dependency triggers fail-fast exit

**Effort: 1-2 weeks | Risk: high (requires restructuring) | Effect: complete isolation, hot-reloadable, version-aware**

## Comparison Matrix

Dimension          Tier 1 (Light)    Tier 2 (Medium)    Tier 3 (Heavy)
------------------------------------------------------------------------
Code changes       0%                30%                80%+
Migration          1-2 days          3-5 days           1-2 weeks
Enforcement        documentation     runtime check      startup/fail-fast
Drift detection    manual            auto alarm         graph validates
Orphan imports     metadata check    runtime intercept  physically isolated
Versioning         __version__ tag   metadata+check     plugin.yaml enforced
Hot-reload         no                no                 partial (registry)
Existing risk      none              medium (imports)   high (restructure)
Guard against
 cross-script
 modification
 impact            low               medium             high

## Integration with data-accuracy-layer

data-accuracy-layer enforces **data quality** within each script (field mappings, cross-validation, chart gates).
script-contract-layer enforces **code quality** between scripts (dependency declarations, interface contracts, drift detection).

They complement each other:

- data-accuracy-layer: data_guard.validate_data() at each pipeline entry point
- script-contract-layer: validate-deps + contract checks at startup and pre-commit

The function drift detector in data-accuracy-layer Layer 5 acts as a **safety net** -- it catches drift after it happens.
Script-contract-layer provides **prevention** -- declare + validate before changes land.

## First Step (Week 1 Plan)

1. List all scripts in writing-data/ and quant/ -- identify every import relationship
2. Write domain.yaml for each cluster (writing, quant)
3. Run validate-deps -- document all undeclared imports and unexported usages
4. Add __interface_version__ to each script (start with "1.0.0")
5. Integrate validate-deps into pre-commit

## See Also

- references/java-modularization-to-python.md -- Full research: JPMS, OSGi, ServiceLoader, and the complete mapping analysis
- data-accuracy-layer -- Data quality enforcement (complementary layer)

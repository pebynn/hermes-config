# Java Modularization to Python Script Governance

## Source Research

Research conducted 2026-05-08 via research-domain. Based on analysis of:

- JPMS (Java Platform Module System, Project Jigsaw - Java 9+)
- OSGi (Open Services Gateway Initiative - dynamic modularity)
- ServiceLoader pattern (provides/uses)
- Interface segregation + dependency inversion principles

## JPMS Core Mechanics

### module-info.java

Every Java 9+ module declares itself in module-info.java at root:

```java
module com.example.mymodule {
    requires java.base;                    // explicit dependency
    requires com.example.anothermodule;
    exports com.example.mymodule.api;      // only public API visible
    exports com.example.mymodule.internal  // qualified: only to specific consumers
        to com.example.plugin.loader;
    opens com.example.mymodule.internal;   // for reflection (DI/ORM frameworks)
    uses com.example.service.MyService;    // service consumer
    provides com.example.service.MyService // service provider
        with com.example.serviceprovider.MyServiceImpl;
}
```

### Key Design Properties

1. **Strong encapsulation by default**: All packages hidden. Only explicitly exported packages are accessible. Even `public` classes in non-exported packages are invisible.

2. **Fail-fast resolution**: JVM builds a module graph at startup. Missing dependencies or split packages prevent launch. Error before any code runs.

3. **No split packages**: Two modules cannot define classes in the same package. Forces clean namespace separation.

4. **Explicit dependencies**: Every `requires` is checked. No silent classpath magic.

### Automatic Modules

JARs without module-info.java on module path become "automatic modules":
- All packages implicitly exported
- Can read unnamed module (classpath)
- Bridge for gradual migration

### Module Path vs Classpath

| Feature | Classpath (Legacy) | Module Path (JPMS) |
|---------|-------------------|-------------------|
| Encapsulation | Weak | Strong (only exported packages visible) |
| Dependencies | Implicit (JAR Hell) | Explicit (requires) |
| Package Rules | Split packages allowed | No split packages allowed |
| Resolution | Flat search, first-come-first-served | Graph-based, strict resolution |
| Runtime Issues | Common (NoClassDefFoundError) | Minimized by early detection |

### Module Resolution Process

1. Identify root modules (the application's main module)
2. Resolve all transitive dependencies
3. Validate no missing or conflicting modules
4. Create module layer (immutable graph)
5. Application startup

## OSGi Key Concepts (Beyond JPMS)

OSGi predates JPMS and goes further in some dimensions:

1. **Bundle lifecycle**: INSTALLED -> RESOLVED -> STARTING -> ACTIVE -> STOPPING -> UNINSTALLED. Runtime hot-plug.

2. **Service Registry**: Bundles don't import classes. They register services and consume services. Loose coupling.

3. **Version ranges**: `import com.example.api; version="[1.0,2.0)"` specifies acceptable range. Much more expressive than JPMS.

4. **Independent ClassLoaders**: Different bundles can have different versions of the same library running simultaneously.

5. **Dynamic**: Services come and go at runtime. Consumers must handle service disappearance.

## Python Mapping Analysis

### What Translates Directly

| Java Concept | Python Equivalent | Difficulty |
|---|---|---|
| module-info.java | domain.yaml | Easy - just a YAML file |
| requires | depends_on: [...] in domain.yaml | Easy - metadata |
| exports | __all__ in __init__.py | Easy - Python built-in |
| exports ... to | @visible_to decorator or import guard | Medium |
| provides/uses | entry_points in setup.cfg / importlib | Medium |
| ServiceLoader | importlib.metadata.entry_points() | Medium (Python 3.9+) |
| Strong encapsulation | Import-level checks at runtime | Hard - no compile-time in Python |

### What Doesn't Translate

| Java Feature | Why Python Can't Replicate |
|---|---|
| Compile-time check | Python has no compile phase for module resolution |
| Split package prevention | Python allows same package across different paths |
| JVM-level isolation | Python has no equivalent to JVM module layer |
| ClassLoader isolation | Python import system is flat per interpreter |
| Access control (module-private) | Python has only public/private convention (underscore) |

### What Must Be Runtime in Python

Since Python lacks compile-time enforcement, all JPMS-like checks must be:
1. **Pre-commit hooks** (static analysis before git commit)
2. **Startup validation** (run validate-deps before any real work)
3. **Runtime interception** (import hooks or registry pattern)
4. **CI/CD gates** (automated checks on push)

## Direct Code Inspection Findings

The research-domain subagent inspected actual Hermes scripts and found:

### signal_engine.py (v4.0, 1062 lines)

```python
# Lines 8-25 show direct imports from multiple scripts:
from chan_buy_signal import detect_chan_buy2      # Interface coupling
from stock_fund_flow import today_total_flow        # Interface coupling
from data_common import get_market, load_all_data    # Interface coupling
```

Problem: Each import is a hard dependency. Changing detect_chan_buy2's signature requires checking signal_engine. No explicit contract.

### daily_signal_report.py (276 lines)

```python
# Line 5: sys.path.insert for non-standard path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from signal_engine import scan_signals
```

Problem: Path manipulation baked into script. Any change to signal_engine's location or interface silently breaks this.

### morning_brief.py (894 lines)

```python
# try/except wrapping imports -- fragile runtime degradation
try:
    from data_bridge import load_today_data
    COMPLETE = True
except ImportError:
    COMPLETE = False
```

Problem: Silent degradation. When data_bridge changes, morning_brief silently skips data. No log, no alert.

### chan_buy_signal.py (452 lines)

```python
# detect_chan_buy2 has no documented return schema -- consumers assume structure
def detect_chan_buy2(kline_df):
    # ... processing ...
    result = pd.DataFrame(...)
    result['buy_signal'] = ...  # added later, not documented anywhere
    return result
```

Problem: Return schema undocumented. Column added in v2 silently propagates to consumers who may or may not handle it.

## Key Insight: YAML as module-info.java

The most practical first step is YAML-based dependency declaration (domain.yaml) because:
1. Zero code change required
2. Machine-readable for automated validation
3. Human-readable for documentation
4. Can be checked into git
5. Enables progressive enhancement (add more fields over time)

## References

- JPMS official JSR 376: https://openjdk.org/projects/jigsaw/
- OSGi Core Specification Release 7: https://docs.osgi.org/specification/
- Python Protocol (PEP 544): https://peps.python.org/pep-0544/
- Python importlib.metadata (PEP 643): https://peps.python.org/pep-0643/

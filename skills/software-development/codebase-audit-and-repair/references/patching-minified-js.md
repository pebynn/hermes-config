# Patching Minified Dashboard JS

Some Hermes dashboard plugins ship only `dist/index.js` — a minified
React bundle with no TypeScript source code available. All frontend fixes
must be done via exact-string `patch()` on the minified output.

## When This Applies

- Plugin directory has `dist/index.js` but no `src/` directory
- The JS is a single minified file (typically 15-25K lines)
- Changes are limited to function logic adjustments or i18n string replacements

## Workflow

### 1. Find Function Boundaries

Use a Python script to locate the function you need to modify:

```python
with open('path/to/dist/index.js') as f:
    js = f.read()

idx = js.find('const functionName = useCallback(function')
if idx >= 0:
    brace = 0
    started = False
    for i in range(idx, min(idx+2000, len(js))):
        if js[i] == '{':
            brace += 1; started = True
        elif js[i] == '}':
            brace -= 1
            if started and brace == 0:
                end = i+1
                break
    print(js[idx:end])  # Full function body
```

### 2. Match Exact Strings

Minified JS is deterministic — variable names and string literals are stable
across builds. Use the exact string from the file as `old_string` in `patch()`.

```python
# ✅ Works: exact match from the file
patch(old_string='title: "Switch kanban board",', new_string='title: tx(...)', ...)

# ❌ Fails: approximate match
patch(old_string='title: switch board', ...)  # Won't match
```

### 3. Verify Indentation

Minified JS has intentional line breaks and indentation for readability.
When inserting new code (e.g. a `.catch()` block or a `useEffect`), match
the surrounding indentation exactly.

**Real fix — adding .catch() to deleteBoard:**
```javascript
// Before:
    }).then(function () {
        loadBoardList();
        if (board === slug) switchBoard("default");
      });
    }
// After:
    }).then(function () {
        loadBoardList();
        if (board === slug) switchBoard("default");
      }).catch(function (err) {
        console.error("Failed to archive board:", err);
        loadBoardList();
      });
    }
```

**Real fix — inserting a new useEffect:**
```javascript
// Match the preceding line's indentation pattern exactly
    useEffect(function () { loadBoardList(); }, [loadBoardList]);

    // New block — indent matches surrounding code
    useEffect(function () {
      function handleVisibility() {
        if (document.visibilityState === "visible") loadBoardList();
      }
      document.addEventListener("visibilitychange", handleVisibility);
      return function () { document.removeEventListener("visibilitychange", handleVisibility); };
    }, [loadBoardList]);
```

### 4. Syntax Validation

After patching, verify the JS is still syntactically valid:

```bash
node -c path/to/dist/index.js 2>&1 || echo "Syntax error (may be pre-existing in minified code)"
```

Note: Some minified bundles intentionally fail `node -c` (e.g. top-level `h()` calls
that look like statements). This is normal for pre-built bundles. Focus on whether
the specific section you edited is well-formed.

### 5. i18n Cross-Cutting Fix Order

When converting hardcoded English strings to i18n:

1. **Add key to `en.ts` first** — this is the source of truth for new keys
2. **Add matching Chinese key to `zh.ts`** — translate, preserve tone
3. **Patch the JS to use `tx(t, "key", "fallback")`** — use the English string as fallback
4. **Verify key sets match**: `grep` for all new keys in both en.ts and zh.ts

Example:
```
# 1. en.ts: add "boardSwitcherTitle: 'Boards are independent...'"
# 2. zh.ts: add "boardSwitcherTitle: '每个看板是独立的工作流...'"
# 3. JS:   title: tx(t, "boardSwitcherTitle", "Boards are independent...")
```

## Real Case: Hermes Kanban Dashboard (2026-05-13)

Fixed 11 issues across 5 files:

| File | Type | Fix |
|:--|:--|:--|
| `plugin_api.py` | Backend | Added `archived` field to `RenameBoardBody` |
| `kanban_db.py` | Backend | Update `board.json` before directory move |
| `dist/index.js` | Frontend | `.catch()` on deleteBoard + visibility listener + 7 tooltip i18n wrappers |
| `en.ts` | i18n | Added 7 translation keys |
| `zh.ts` | i18n | Added 7 translation keys with proper Chinese |

# 代码库卫生扫描模式 (Codebase Hygiene Scan Patterns)

从多轮 code-domain 审计/修复会话中提炼的扫描模式。每次接到「审查代码」「修问题」「过一遍」等需求时，按此清单执行。

## 1. 硬编码凭据扫描 (Hardcoded Credentials)

### 扫描目标
读取 `.py`、`.yaml`、`.json`、`.sh` 文件中的明文密码/API key/token。

### 扫描模式

```bash
# 模式1: password="xxx" 或 password = "xxx"
rg '(password|passwd|pwd)\s*=\s*["'']' --type py -n

# 模式2: api_key="xxx" 或 api_key = "xxx" (非环境变量引用)
rg 'api_key\s*=\s*["''](?!\$)' --type py -n

# 模式3: token="xxx" 硬编码 (非 ".env" 等上下文)
rg '(token|secret)\s*=\s*["'']' --type py -n | rg -v '(getenv|environ\.get|os\.get)'

# 模式4: 连接串中的密码 (mysql://user:***@...)
rg '://[^:]+:***@' --type py -n

# 模式5: 任何 .env 变量名被硬编码替代
rg 'os\.environ\.get\([^)]+"'  --type py -n  # 有 fallback 值
rg 'os\.getenv\("[A-Z_]+",\s*["'']' --type py -n  # 有 fallback 值
```

### 修复原则

- 所有硬编码密码 → 替换为 `os.getenv("MYSQL_PASSWORD", "")`（fallback为空串，使不设环境变量时优雅失败）
- 确保所有使用同一 `MYSQL_PASSWORD` 的文件使用相同的 env 变量名
- 不要混用不同 env 变量名（如 `DB_PASSWORD` vs `MYSQL_PASSWORD` → 统一）
- 对于 MySQL 连接，pymysql 和 SQLAlchemy URL 都要改

### 实战案例: 8处硬编码 `stock123`

| 文件 | 改前 | 改后 |
|:-----|:-----|:-----|
| `backfill_kline.py:9` | `password="stock123"` | `password=os.getenv("MYSQL_PASSWORD", "")` |
| `db_web.py:10` | `os.environ.get("DB_PASSWORD", "stock123")` | `os.environ.get("MYSQL_PASSWORD", "")` |

## 2. 静默异常扫描 (Silent Exception Detection)

### 危险级别分级

| 模式 | 危险级 | 说明 |
|:-----|:-------|:-----|
| `except: pass` | 🔴 P0 | 吞所有异常，调试灾难 |
| `except Exception: pass` | 🔴 P0 | 同上，稍窄 |
| `except: continue` | 🔴 P1 | 循环中吞异常继续，可能跳过关键数据 |
| `except: return None` | 🟠 P2 | 调用方需处理 None |
| `except Exception:` (裸块) | 🟠 P2 | 无变量名，无法 traceback |
| `except X as e:` (体只有 pass) | 🟡 P3 | 有变量但不用，可能遗漏 |

### 批量修复脚本

```python
import os, re

def fix_silent_excepts(filepath):
    """遍历文件，在 silent except 块首行插入 traceback.print_exc()"""
    with open(filepath, 'r') as f:
        content = f.read()
    lines = content.split('\n')
    
    has_tb = 'import traceback' in content
    needs_tb = False
    modified = False
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 匹配 except: / except X: / except X as Y: 模式
        pat = re.match(r'^(\s*)except\s*(?:\w+(?:\s+as\s+\w+)?)?\s*:\s*$', stripped)
        if not pat:
            new_lines.append(line)
            i += 1
            continue
        
        except_indent = len(line) - len(line.lstrip())
        
        # 收集 body 行
        j = i + 1
        body_lines = []
        while j < len(lines):
            l = lines[j]
            if l.strip() == '':
                body_lines.append(l)
                j += 1
                continue
            indent = len(l) - len(l.strip())
            if indent <= except_indent:
                break
            body_lines.append(l)
            j += 1
        
        # 判断是否静默
        has_output = False
        for bl in body_lines:
            s = bl.strip()
            if any(kw in s for kw in ['traceback', 'print(', 'print (', 'log.', 'logger.', 'logging.', 'raise ']):
                has_output = True
                break
        
        if has_output:
            new_lines.append(line)
            new_lines.extend(body_lines)
            i = j
            continue
        
        # 静默 → 插入 traceback.print_exc()
        needs_tb = True
        modified = True
        new_lines.append(line)
        tb_line = ' ' * (except_indent + 4) + 'traceback.print_exc()'
        new_lines.append(tb_line)
        new_lines.extend(body_lines)
        i = j
    
    if not modified:
        return False
    
    result = '\n'.join(new_lines)
    
    # 确保有 import traceback
    if needs_tb and not has_tb:
        lines_r = result.split('\n')
        insert_pos = 0
        for idx, l in enumerate(lines_r):
            s = l.strip()
            if s.startswith('import ') or s.startswith('from '):
                if 'from __future__' not in s:
                    insert_pos = idx + 1
        lines_r.insert(insert_pos, 'import traceback')
        result = '\n'.join(lines_r)
    
    with open(filepath, 'w') as f:
        f.write(result)
    return True
```

### 批量扫描/修复命令

```bash
# 扫描所有 silent except 块
python3 -c "
import os, re
for root, dirs, files in os.walk('/home/pebynn/quant'):
    for f in files:
        if not f.endswith('.py'): continue
        fp = os.path.join(root, f)
        with open(fp) as fh: content = fh.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() in ('except:', 'except Exception:'):
                # 检查 body 是否有输出
                ...
                print(f'{fp}:{i+1} silent except')
"

# 批量修复（使用上述 fix_silent_excepts 函数）
for d in ['/home/pebynn/quant', '/home/pebynn/.hermes/scripts']:
    for root, dirs_, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                fix_silent_excepts(os.path.join(root, f))
```

### 重要排除

以下模式无需加 traceback（是故意静默的合法场景）:

- `except ImportError: pass` — 可选依赖 fallback
- `except (ValueError, TypeError): return None` — 严格类型转换保护
- `except (KeyError, IndexError): continue` — 遍历不完整数据时的弹性处理
- 带 `_log(...)` 或 `logger.warn(...)` 的 except 块（已有日志）

## 3. 函数体漂移检测 (Function Body Drift Detection)

### 问题
跨文件同名函数因分别修改导致行为不一致。`safe_float()` 在 7 个文件中各有实现，`scrub_ai_vocabulary()` 在 3 个文件中不一致。

### 检测方法

```python
import ast, hashlib

SCAN_DIRS = [
    '/home/pebynn/quant',
    '/home/pebynn/.hermes/scripts',
    '/home/pebynn/writing-data/scripts',
]

def detect_func_drift():
    """返回所有出现 >=2 次但 body hash 不同的函数"""
    funcs = {}  # name -> [{path, hash}]
    for d in SCAN_DIRS:
        for root, dirs_, files in os.walk(d):
            if 'archive' in root: continue
            for f in files:
                if not f.endswith('.py'): continue
                fp = os.path.join(root, f)
                try:
                    tree = ast.parse(open(fp).read())
                except: continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        source = ast.unparse(node)
                        h = hashlib.md5(source.encode()).hexdigest()
                        funcs.setdefault(node.name, []).append({
                            'path': fp, 'hash': h, 'name': node.name
                        })
    
    drift = []
    for name, instances in funcs.items():
        if name.startswith('_'): continue
        hashes = set(i['hash'] for i in instances)
        if len(hashes) > 1 and len(instances) > 1:
            drift.append({
                'func': name,
                'locations': [(i['path'], i['hash']) for i in instances],
                'variants': len(hashes),
            })
    
    # 按 variant 数降序排列
    drift.sort(key=lambda x: -x['variants'])
    return drift
```

### 判断标准

| 关系 | 含义 | 操作 |
|:-----|:-----|:-----|
| 完全一致 hash | copy-paste 副本 | 合并到 shared/ 或采用 import |
| 同签名不同 body | 自然演化但可能 drift | 确认意图是否一致，否则改名 |
| 签名也不同 | 已独立演化 | 保留，不处理 |
| 一个 return stub 一个有实现 | 不同层级（stub-layer vs impl-layer） | stub 应 import 完整实现 |

## 4. 实战效果

2026-05-10 一次执行修复：

| 类别 | 数据 |
|:-----|:-----|
| 扫描文件总数 | ~100 .py 文件 |
| 硬编码密码修复 | 2 处（backfill_kline.py, db_web.py） |
| 静默异常修复 | 139 处 traceback.print_exc() 插入 |
| 修改文件数 | 29 个文件 |
| 函数名重复数 | 30 组 |
| 真正需合并的 drift | 1 组：get_trading_calendar 3个副本 |
| Generator模式 | 2 组：pipeline_stage_1_protocol 生成 contracts 文件，非 drift |

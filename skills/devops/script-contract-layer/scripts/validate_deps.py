#!/usr/bin/env python3
"""
validate-deps: Script contract integrity scanner.

Reads domain.yaml, scans all .py files in the cluster, and validates:
1. Every import matches depends_on declarations
2. Every consumed function is in exports of the supplier
3. No circular dependencies
4. __interface_version__ exists on every script
5. No orphan imports (import of something not in any domain.yaml)

Usage:
    python3 validate_deps.py [--domain writing-data/hermes-domain.yaml]

Exit codes:
    0 - All checks pass
    1 - Warnings only (undocumented imports)
    2 - Errors found (circular deps, missing exports, broken contracts)
"""

import ast
import os
import sys
import yaml
from pathlib import Path
from collections import defaultdict


def load_domain(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def extract_imports(py_path: str) -> list:
    """Extract all import statements from a Python file."""
    with open(py_path) as f:
        try:
            tree = ast.parse(f.read(), filename=py_path)
        except SyntaxError as e:
            return [{"error": f"SyntaxError: {e}", "line": 0}]

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from",
                    "module": module,
                    "name": alias.name,
                    "line": node.lineno,
                })
    return imports


def resolve_script_path(script_name: str, script_dir: str) -> str:
    """Map script name to file path. Supports .py suffix and bare names."""
    if script_name.endswith(".py"):
        return str(Path(script_dir) / script_name)
    candidates = [
        Path(script_dir) / f"{script_name}.py",
        Path(script_dir) / script_name / "__init__.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def check_circular_dep(domain: dict) -> list:
    """Detect circular dependencies between scripts."""
    graph = {}
    for name, info in domain.get("scripts", {}).items():
        graph[name] = set(info.get("depends_on", []))

    cycles = []
    visited = set()
    path = []

    def dfs(node):
        if node in path:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(" -> ".join(cycle))
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for neighbor in graph.get(node, set()):
            if neighbor in graph:  # only follow known scripts
                dfs(neighbor)
        path.pop()

    for node in graph:
        dfs(node)

    return cycles


def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("--domain="):
        domain_path = sys.argv[1].split("=", 1)[1]
    else:
        # Auto-discover
        for candidate in ["hermes-domain.yaml", "domain.yaml"]:
            if Path(candidate).exists():
                domain_path = candidate
                break
        else:
            print("ERROR: No domain.yaml found. Pass --domain=<path>")
            sys.exit(1)

    domain = load_domain(domain_path)
    script_dir = os.path.dirname(os.path.abspath(domain_path))
    domain_name = domain.get("domain", "unknown")
    version = domain.get("version", "0.0.0")

    print(f"=== validate-deps: {domain_name} v{version} ===")
    print(f"Script dir: {script_dir}\n")

    errors = []
    warnings = []
    scripts = domain.get("scripts", {})

    if not scripts:
        print("WARNING: No scripts declared in domain.yaml")
        sys.exit(0)

    # Build reverse dependency map
    consumers_of = defaultdict(list)
    for name, info in scripts.items():
        for dep in info.get("depends_on", []):
            consumers_of[dep].append(name)

    # Check each script
    for script_name, script_info in scripts.items():
        script_path = resolve_script_path(script_name, script_dir)
        if not script_path or not os.path.exists(script_path):
            errors.append(f"[{script_name}] File not found")
            continue

        # Check: __interface_version__
        with open(script_path) as f:
            content = f.read()

        if "__interface_version__" not in content:
            warnings.append(f"[{script_name}] Missing __interface_version__")

        # Check: imports match depends_on
        imports = extract_imports(script_path)

        for imp in imports:
            if "error" in imp:
                warnings.append(f"[{script_name}] Parse error: {imp['error']}")
                continue

            # Skip standard library and third-party imports
            module = imp["module"]
            if module.startswith(("os", "sys", "json", "re", "math", "time",
                                  "datetime", "collections", "pathlib",
                                  "typing", "pandas", "numpy", "yaml",
                                  "pymysql", "requests", "selenium")):
                continue

            # Skip internal module references
            if module.startswith("_"):
                continue

            # Check if imported script is in depends_on
            from_name = imp.get("name", "")
            # Try to match: import signal_engine -> depends_on has signal_engine
            declared_deps = script_info.get("depends_on", [])
            matched = False
            for dep in declared_deps:
                dep_base = dep.replace(".py", "")
                if module == dep_base or from_name == dep_base:
                    matched = True
                    break

            if not matched:
                warnings.append(
                    f"[{script_name}] Line {imp['line']}: imports '{module}' "
                    f"but it is not in depends_on: {declared_deps}"
                )

            # Check: imported function is in exporter's exports
            # Module-level check: module should match a script name
            lookup_name = module.replace(".py", "")
            if lookup_name in scripts:
                exporter_info = scripts[lookup_name]
                exported_funcs = exporter_info.get("exports", [])
                if from_name and from_name not in exported_funcs:
                    warnings.append(
                        f"[{script_name}] Line {imp['line']}: imports '{from_name}' "
                        f"from '{lookup_name}', but '{lookup_name}' does not "
                        f"export '{from_name}'. Exports: {exported_funcs}"
                    )

    # Check circular dependencies
    cycles = check_circular_dep(domain)
    for cycle in cycles:
        errors.append(f"Circular dependency: {cycle}")

    # Summary
    print(f"Checked {len(scripts)} scripts\n")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [ERROR] {e}")
        print()

    if not warnings and not errors:
        print("All checks passed.")
        sys.exit(0)
    elif errors:
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

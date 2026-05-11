# Python Async Context 缩进验证

## 问题模式

子代理生成的浏览器自动化脚本容易出现缩进错误，`async with` 块提前闭合导致浏览器在 `page.goto` 前关闭。

### 典型症状

```
Page.goto: Target page, context or browser has been closed
BrowserContext.close: Target page, context or browser has been closed
```

### 根本原因

`async with async_playwright() as p:` 块内代码需要一致缩进。如果某行缩进减少，Python 解释器认为 `async with` 块已结束，context 在引用前就被释放。

### 示例（错误）

```python
    async with async_playwright() as p:    # 4空格
        context = await p.chromium.launch_persistent_context(...)  # 8空格
        page = await context.new_page()    # 8空格
        success = False                    # 8空格
    try:                                   # 4空格 ← 错！闭合了 async with
        if args.check_only:
            await page.goto(url)           # context 已关闭，page 无效！
```

### 修复（正确）

```python
    async with async_playwright() as p:    # 4空格
        context = await p.chromium.launch_persistent_context(...)  # 8空格
        page = await context.new_page()    # 8空格
        success = False                    # 8空格
        try:                               # 8空格 ← 在 async with 内
            if args.check_only:            # 12空格
                await page.goto(url)
```

## 验证步骤

每次修改脚本后必须：

```bash
python3 -c "import py_compile; py_compile.compile('script.py', doraise=True)"
```

编译通过不代表逻辑正确，但至少没有语法错误。

## patch 缩进注意事项

使用 `patch` 工具修改缩进时：
1. 始终用精确的空格数（不依赖 tab）
2. 修改后立即验证语法
3. 关注 `async with` / `try` / `except` / `finally` 的层级关系
4. 如果改动超过10行，用 `py_compile` 验证

## 相关案例

- PDD 脚本：多次缩进错误
- coding_plan_sniper.py：line 766 try 缩进闭合 async with → browser closed
- --now patch：if args.now 少缩进4空格 → 闭合 try 块

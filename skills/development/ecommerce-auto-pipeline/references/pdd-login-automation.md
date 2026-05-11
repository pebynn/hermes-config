# PDD 商家后台登录自动化 — 实战记录

> 2026-05-01 会话全程记录。从 scrapling 到原生 Playwright 的实操路径。

## 最终方案：原生 Playwright + 先 headed 后 headless

**文件：** `~/PDD/pdd_login_v2.py`（557行，可执行）

### 为什么没用 scrapling

| 问题 | 细节 |
|:--|:--|
| `real_chrome=True` | 需要 `/opt/google/chrome/chrome`，系统未装 |
| `StealthySession` EPIPE | Node.js v24.13.0 下 patchright 与 playwright driver 的 pipe 断开，退出清理阶段崩溃 |
| 实际表现 | page_action 成功执行（切Tab/填表/点登录），但退出时 EPIPE 导致脚本异常终止 |

### v2 方案（Playwright 原生）

```bash
# 首次：有界面模式，手动过滑块
python3 ~/PDD/pdd_login_v2.py --headed

# 后续：无界面复用 auth 文件
python3 ~/PDD/pdd_login_v2.py

# 检查会话
python3 ~/PDD/pdd_login_v2.py --check
```

**关键设计：**
- 原生 `playwright.sync_api`，无 scrapling 依赖
- Stealth：`add_init_script` 注入 JS 覆盖 `navigator.webdriver` + `--disable-blink-features=AutomationControlled`
- 会话持久化：`context.storage_state(path='~/.pdd_auth.json')`
- headed 模式：检测滑块 → 提示用户手动完成 → 轮询检测登录成功（最长 5 分钟）
- headless 模式：自动尝试滑块求解（但 PDD 缺口匹配型滑块成功率为 0）

### 已验证的页面特征

- 登录页：`https://mms.pinduoduo.com/login/`，React 16 SPA
- Tab 切换：`text=账号登录` 可定位
- 输入框：`#usernameId` / `#passwordId`
- 登录按钮：`button:has-text('登录')`
- 滑块验证码：缺口匹配型，轨道宽度约 411px，滑块按钮约 (435, 309)
- 弹窗干扰：`beast-core-modal` 可能遮挡点击，`query_selector.click()` 比 `locator.click()` 更容错
- 滑块自动求解 8+ 轮全失败 — 必须 headed 手动过一次

### 凭据

账号：18125973593（代码中硬编码，可通过 `MMS_USERNAME` / `MMS_PASSWORD` 环境变量覆盖）

### 后续复用 auth 文件

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state="~/.pdd_auth.json")
    page = context.new_page()
    page.goto("https://mms.pinduoduo.com/home/")
    # 已登录，直接操作
```

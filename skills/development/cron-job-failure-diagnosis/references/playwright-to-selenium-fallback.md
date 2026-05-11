# Playwright → Selenium 应急转换指南

## 触发条件

当 Playwright 在指定系统上出现以下症状时，说明 pipe 机制不可用，需切换到 Selenium：

- `BrowserType.launch: Timeout 180000ms exceeded`
- 浏览器进程正常启动但 `waitForReadyState` 永久挂起
- 直接运行 Chromium 报告 `Remote debugging pipe file descriptors are not open`
- 用 `--remote-debugging-port=0` 直接启动 Chromium 正常，但 Playwright 坚持使用 `--remote-debugging-pipe`

## 根因

Playwright 默认使用 `--remote-debugging-pipe` 进行 CDP 通信（通过子进程的 fd[3] 和 fd[4] 传递管道描述符）。在某些系统配置下（如 Wayland + Xwayland 混合环境），pipe FD 传递机制失败，导致 Playwright 永远收不到浏览器就绪信号。

Playwright 的 `supportsPipeTransport()` 返回 `true`，且 `defaultArgs()` 硬编码 `--remote-debugging-pipe`。即使用户传入 `--remote-debugging-port=0`，Playwright 也会抛出错误阻止。仅修补 `defaultArgs` 不够——`waitForReadyState` 的另一条路径仍会走 pipe 传输层。

## API 映射表

| Playwright (async) | Selenium (sync) |
|:--|:--|
| `async_playwright()` | `webdriver.Chrome(options=opts)` |
| `launch_persistent_context(user_data_dir=...)` | `opts.add_argument(f"--user-data-dir={path}")` |
| `page.locator(".selector")` | `driver.find_element(By.CSS_SELECTOR, ".selector")` |
| `page.locator("text=xxx").first` | `driver.find_element(By.XPATH, "//*[contains(text(),'xxx')]")` |
| `page.query_selector_all(sel)` | `driver.find_elements(By.CSS_SELECTOR, sel)` |
| `await card.inner_text()` | `card.text` |
| `await page.click()` / `element.click()` | `element.click()` |
| `await page.screenshot(path=str(p))` | `driver.save_screenshot(p)` |
| `wait_for_selector(sel)` | `WebDriverWait(driver, t).until(EC.presence_of_element_located(...))` |
| `page.locator("xpath=ancestor::*[...][1]")` | `el.find_element(By.XPATH, "./ancestor::*[...][1]")` |
| `locator.count() > 0` | `try/except NoSuchElementException` |

## 关键配置

```python
opts = Options()
opts.add_argument(f"--user-data-dir={USER_DATA_DIR}")  # 持久化 profile (登录态)
opts.add_argument("--remote-debugging-port=0")         # 避免 pipe 模式
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
# 反检测:
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
```

## 注意事项

1. **async → sync**: 去掉所有 `async`/`await`，函数定义改为普通 `def`
2. **错误处理**: Playwright 用 `try/except` 包裹定位器操作，Selenium 用 `try/except NoSuchElementException`
3. **WebDriver 生命周期**: 必须在 `finally` 块中 `driver.quit()`，否则 Chrome 进程残留
4. **页面等待**: Selenium 没有 Playwright 的自动等待机制，需显式 `time.sleep()` 或 `WebDriverWait`
5. **CDP pipe 绕过**: `--remote-debugging-port=0` 让 Chrome 分配随机端口，Selenium 通过该端口通信
6. **Profile 锁**: 如果已有 Chrome 实例使用同一 profile，会触发 `SingletonLock` 错误。解决：关掉现有 Chrome 或使用 `--clean-profile`

## 已知限制

- Selenium 没有 Playwright 的 `page.route()` 网络拦截（需要 `selenium-wire` 或 `CDP` 直连）
- 部分动态页面需要更长的显式等待
- 系统 Chromium snap 版本可能与 Playwright 自带的 Chromium 版本不一致，选择器行为可能有微小差异

## 相关案例

- 2026-05-10: `coding_plan_sniper.py` (Playwright) → `coding_plan_sniper_selenium.py` (Selenium) — 智谱 Coding Plan Pro 抢购脚本因 pipe 故障完全无法工作，Selenium 版编译通过待测试

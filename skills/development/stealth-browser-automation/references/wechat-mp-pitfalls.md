# WeChat Official Account Browser Automation Pitfalls

## Login Approaches (from hardest to easiest)

### 1. QR Code Scan (Playwright)
- Opens mp.weixin.qq.com → displays QR code
- User must scan with WeChat app within timeout (5 min)
- **Failed**: user didn't scan in time, process interrupted before state save
- **EPIPE crash** on Node v24 in headless mode — use headful only
- Detection: poll URL for `cgi-bin/home` every 2s

### 2. Password Login (Playwright)
- Click "使用账号登录" → fill account + password → click `.btn_login`
- **Failed**: login button click submits form but URL doesn't redirect
- WeChat MP anti-bot detection silently blocks automated password login
- Even with `--disable-blink-features=AutomationControlled` and `navigator.webdriver` override
- Slow typing simulation (100ms/char delay) did not help

### 3. Cookie-Based API (✅ WORKS)
- Manual login once → extract cookies → use cookies for API calls
- See `references/cookie-publishing.md` in a-share-content-automation skill
- This is the recommended approach

## stdout Buffering Issue

When running Playwright scripts via Hermes terminal tool, `print()` output may not appear due to stdout buffering:
- `python3 -u` flag helps but doesn't fully solve
- stderr often shows up before stdout
- Best practice: write status to a file, poll from separate terminal calls

## Node v24 EPIPE Crash

Headless Playwright on Node v24 crashes with:
```
Error: write EPIPE
    at PipeTransport.send (...)
    Node.js v24.13.0
```

Workaround: use `headless=False` (requires DISPLAY). Sessions that need headless should use `--headless=new` or downgrade Node.

## Storage State Race Condition

When user sends a message during `context.storage_state()` call, the process gets SIGINT before cookies are written to disk. Fix: save storage_state IMMEDIATELY after login detection, in the login polling loop itself, before returning to the main function.

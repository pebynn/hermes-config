# OS-Level Input Bypass for React/SPA Automation

Condensed technical reference. Full report: ~/docs/pyautogui-xvfb-feasibility-report.md

## The Core Problem

React production mode + custom component libraries (beast-core) reject DOM-level input injection via three defense layers:
1. `isTrusted` check — `dispatchEvent()` produces `isTrusted: false` → rejected
2. React synthetic event delegation at document root — native DOM events may not enter React pipeline
3. Component-level validation — `Object.defineProperty` overrides on input.value setter

## OS-Level Bypass (PyAutoGUI + Xvfb)

PyAutoGUI on Linux uses X11 **XTEST extension** (`XTestFakeKeyEvent`, `XTestFakeButtonEvent`), not `XSendEvent`. XTEST injects events through the kernel input subsystem, making them indistinguishable from real hardware events. Browsers mark them `isTrusted: true`.

Flow: `PyAutoGUI.click() → XTEST → kernel → Chromium → isTrusted:true → React synthetic events → beast-core normal processing`

## Critical Constraint: Window Focus

PyAutoGUI operates on the entire X11 screen, not a specific window. Focus management is the #1 failure mode. Mitigations: `page.bring_to_front()` before each action, dismiss popups before clicking, OCR-based popup detection.

## CDP Input.* as Lighter Alternative

Chrome DevTools Protocol `Input.dispatchKeyEvent` / `Input.dispatchMouseEvent` also produce `isTrusted: true` events WITHOUT needing Xvfb. Always test CDP first before committing to full OS-level automation.

## Positioning Strategy (ranked)

1. CSS selectors (Playwright) — still use when possible
2. OpenCV template matching — most reliable for OS-level clicking
3. pytesseract OCR — fallback for text-labeled elements
4. Color-based — PDD brand colors are stable
5. Fixed coordinates — last resort, fragile

## Key Commands

```bash
# Xvfb
Xvfb :99 -screen 0 1920x1080x24 -ac &
export DISPLAY=:99

# Dependencies
sudo apt-get install xvfb scrot tesseract-ocr tesseract-ocr-chi-sim wmctrl xdotool
pip install pyautogui pillow opencv-python pytesseract pyvirtualdisplay python3-xlib
```

## Sources
- MDN Event.isTrusted: https://developer.mozilla.org/en-US/docs/Web/API/Event/isTrusted
- React synthetic events: https://legacy.reactjs.org/docs/events.html
- X11 XTEST: https://bharathisubramanian.wordpress.com/2010/03/14/x11-fake-key-event-generation-using-xtest-ext/
- CDP Input domain: https://chromedevtools.github.io/devtools-protocol/tot/Input/
- PyAutoGUI headless: https://stackoverflow.com/questions/39137476/is-it-possible-to-run-pyautogui-in-headless-mode

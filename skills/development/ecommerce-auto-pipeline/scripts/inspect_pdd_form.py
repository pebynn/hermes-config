#!/usr/bin/env python3
"""
inspect_pdd_form.py — 探查 PDD 商品发布表单 DOM 结构
确认 SKU 表格列顺序、拼单价/单买价字段位置、商品参考价字段

用法:
  python inspect_pdd_form.py          # headed 模式，30s 观察窗口
  python inspect_pdd_form.py --save   # 保存到自定义路径

前置条件:
  - ~/.pdd_auth.json 存在（已登录会话）
  - playwright 已安装（pip install playwright && playwright install chromium）

输出:
  ~/PDD/form_structure.json           # 原始 DOM 提取（所有 table/input/price 文本）
  ~/PDD/form_analysis.json            # 格式化列顺序分析（推荐的列序号+选择器）
"""

import json, os, sys, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("inspect_pdd_form")

AUTH_FILE = os.path.expanduser("~/.pdd_auth.json")
OUTPUT_STRUCTURE = os.path.expanduser("~/PDD/form_structure.json")
OUTPUT_ANALYSIS = os.path.expanduser("~/PDD/form_analysis.json")
CATEGORY_URL = "https://mms.pinduoduo.com/goods/category"
GOODS_ADD_URL = "https://mms.pinduoduo.com/goods/goods_add/index"

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
"""


def extract_structure(page):
    """提取页面的表格、输入框、SKU 区域结构"""
    result = {
        "current_url": page.url,
        "tables": [],
        "inputs": [],
        "sku_tables": [],
        "price_labels_context": {},
    }

    # 所有表格列标题
    result["tables"] = page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            const out = [];
            tables.forEach((t, idx) => {
                const headers = [];
                t.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim()));
                t.querySelectorAll('[class*="header"] [class*="cell"], [class*="thead"] [class*="cell"]')
                    .forEach(c => headers.push(c.textContent.trim()));
                out.push({idx, tag: t.tagName, id: t.id, cls: t.className.slice(0,200),
                           headers, rows: t.querySelectorAll('tr').length});
            });
            return out;
        }
    """)

    # 所有可见输入框
    result["inputs"] = page.evaluate("""
        () => {
            const inputs = document.querySelectorAll('input');
            const out = [];
            inputs.forEach((inp, idx) => {
                const p = inp.getAttribute('placeholder') || '';
                const t = inp.getAttribute('type') || 'text';
                if (t === 'hidden' || t === 'checkbox' || t === 'radio') return;
                const r = inp.getBoundingClientRect();
                if (r.width === 0 && r.height === 0) return;
                out.push({idx, placeholder: p, id: inp.id,
                          cls: inp.className.slice(0,80), type: t,
                          size: {w: Math.round(r.width), h: Math.round(r.height)}});
            });
            return out;
        }
    """)

    # SKU 表详细行结构
    result["sku_tables"] = page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            const out = [];
            tables.forEach(t => {
                const html = t.outerHTML;
                if (!html.includes('拼单价') && !html.includes('单买价') && !html.includes('库存')) return;
                const rows = t.querySelectorAll('tr');
                const rowData = [];
                rows.forEach((row, ri) => {
                    const cells = row.querySelectorAll('th, td');
                    cellTexts = [];
                    cells.forEach(c => cellTexts.push(c.textContent.trim().slice(0,60)));
                    rowData.push({row: ri, cells: cellTexts});
                });
                out.push({cls: t.className.slice(0,120), rows: rowData});
            });
            return out;
        }
    """)

    # 拼单价/单买价/库存 文本上下文
    result["price_labels_context"] = page.evaluate("""
        () => {
            const body = document.body.innerHTML;
            const find = p => { const r = new RegExp(p,'gi'); const m=[]; let x;
                while((x=r.exec(body)) !== null) m.push(body.slice(Math.max(0,x.index-60),x.index+x[0].length+60));
                return m; };
            return {pintuan: find('拼单价'), danmai: find('单买价'), stock: find('库存')};
        }
    """)

    return result


def build_analysis(structure):
    """从提取的结构生成格式化分析"""
    sku_cols = None
    for t in structure.get("tables", []):
        if t["headers"] and "拼单价" in str(t["headers"]):
            sku_cols = t["headers"]
            break
    if structure.get("sku_tables"):
        sku_cols = structure["sku_tables"][0]["rows"][0]["cells"]

    analysis = {
        "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M"),
        "page_url": structure.get("current_url", ""),
        "sku_table": {},
        "global_price_fields": [],
        "key_findings": {},
        "recommended_selectors": {},
    }

    if sku_cols:
        analysis["sku_table"] = {
            "column_count": len(sku_cols),
            "columns": [
                {"index": i, "name": name.strip(),
                 "css_selector": f'td:nth-child({i+1}) input',
                 "is_price": "拼单价" in name or "单买价" in name,
                 "is_stock": "库存" in name}
                for i, name in enumerate(sku_cols)
            ],
        }
        analysis["key_findings"]["finding_1"] = {
            "title": "SKU表格列顺序",
            "detail": " → ".join(f"{i+1}.{n.strip()}" for i, n in enumerate(sku_cols)),
        }

    # Find market_price input
    for inp in structure.get("inputs", []):
        if "应大于商品最大单买价" in inp.get("placeholder", ""):
            analysis["global_price_fields"].append({
                "name": "商品参考价（市场价/一口价）",
                "selector": f'#market_price input[placeholder*="应大于商品最大单买价"]',
                "placeholder": inp["placeholder"],
            })
            analysis["key_findings"]["finding_5"] = {
                "title": "商品参考价验证规则",
                "detail": f"必须大于所有SKU中最大的单买价。placeholder='{inp['placeholder']}'",
            }

    # Build recommended selectors
    analysis["recommended_selectors"] = {
        "sku_table": '[data-e2e-id="e2e-sku-table"] table',
        "sku_table_header": '[data-e2e-id="e2e-sku-table"] thead th',
        "sku_row": '[data-e2e-id="e2e-sku-table"] tbody tr',
    }
    if sku_cols:
        for i, name in enumerate(sku_cols):
            key = f"{'stock' if '库存' in name else 'pintuan' if '拼单价' in name else 'danmai' if '单买价' in name else 'spec_code' if '规格编码' in name else 'goods_code' if '商品编码' in name else 'other'}_input"
            analysis["recommended_selectors"][key] = \
                f'[data-e2e-id="e2e-sku-table"] tbody tr td:nth-child({i+1}) input'

    analysis["key_findings"]["finding_2"] = {
        "title": "拼单价/单买价仅在SKU表格内",
        "detail": "没有全局'拼单价'字段。唯一全局价格字段是'商品参考价'（在表格下方）。",
    }
    analysis["key_findings"]["finding_3"] = {
        "title": "拼单价和单买价使用相同DOM结构",
        "detail": "两者都使用 div.sku-beast-price-input-container > inputNumber(min=0)，仅通过列位置(nth-child)区分。不能用类选择器定位。",
    }
    analysis["key_findings"]["finding_4"] = {
        "title": "单买价至少比拼单价高1元错误原因",
        "detail": "每行独立校验：单买价(第3列) >= 拼单价(第2列)。触发原因：列顺序写反、同值两列、或实际值违反规则。",
    }

    return analysis


def main():
    import argparse
    parser = argparse.ArgumentParser(description="探查 PDD 商品发布表单 DOM 结构")
    parser.add_argument("--save", help="保存路径（默认 ~/PDD/）")
    parser.add_argument("--headed", action="store_true", default=True,
                       help="headed 模式（默认启用，表单是SPA需要手动观察）")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 必须 headed，表单是 SPA
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        context.add_init_script(STEALTH_JS)

        if Path(AUTH_FILE).exists():
            with open(AUTH_FILE) as f:
                context.add_cookies(json.load(f).get("cookies", []))
            log.info("已加载登录会话")
        else:
            log.error(f"未找到 auth 文件: {AUTH_FILE}")
            return 1

        page = context.new_page()

        # 导航到分类页面 → 选分类 → 进入表单
        log.info("导航到分类页面")
        page.goto(CATEGORY_URL, wait_until="networkidle")
        time.sleep(3)

        # 搜索分类
        try:
            search_input = page.locator('input[placeholder*="搜索分类"], input[placeholder*="请输入关键词"]')
            search_input.wait_for(timeout=10000)
            search_input.fill("中老年女装")
            time.sleep(2)
        except Exception as e:
            log.warning(f"分类搜索失败: {e}")

        # 点击确认发布
        try:
            confirm = page.locator('button:has-text("确认发布该类商品")')
            if confirm.count() > 0:
                confirm.click()
        except Exception:
            pass

        # 等待跳转
        try:
            page.wait_for_url("**/goods/goods_add/**", timeout=15000)
        except PwTimeout:
            page.goto(GOODS_ADD_URL, wait_until="networkidle")

        time.sleep(5)
        log.info(f"已进入表单页: {page.url}")

        # 提取结构
        structure = extract_structure(page)
        analysis = build_analysis(structure)

        # 保存
        base = args.save or os.path.expanduser("~/PDD/")
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "form_structure.json"), "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        with open(os.path.join(base, "form_analysis.json"), "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        log.info(f"结构 → {base}/form_structure.json")
        log.info(f"分析 → {base}/form_analysis.json")

        # 打印摘要
        print("\n=== SKU 表格列顺序 ===")
        sku = analysis.get("sku_table", {})
        for col in sku.get("columns", []):
            marker = " <-- 价格字段" if col.get("is_price") else ""
            print(f"  第{col['index']+1}列: {col['name']}{marker}")

        print("\n=== 推荐选择器 ===")
        for k, v in analysis.get("recommended_selectors", {}).items():
            print(f"  {k}: {v}")

        print("\n等待 30 秒供观察...")
        time.sleep(30)
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

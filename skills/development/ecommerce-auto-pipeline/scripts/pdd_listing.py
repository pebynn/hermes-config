#!/usr/bin/env python3
"""
拼多多商家后台自动上架工具 v1.0
使用 Playwright 模拟登录 mms.pinduoduo.com 并自动发布商品

流程：
  1. 登录（QR码扫码，storage_state持久化）
  2. 导航到商品发布页 /goods/add
  3. 填写基础信息（标题、分类、价格、库存）
  4. 上传主图和详情图（file chooser）
  5. 填写SKU规格（颜色+尺码）
  6. 填写必填项（发货时间48h、重量0.5kg）
  7. 提交或预览

用法：
    # 预览（不提交）
    python pdd_listing.py --input /home/pebynn/PDD/商品/2026-04-27/full_flow/卡彤网批-001 --preview

    # 发布单个商品
    python pdd_listing.py --input /home/pebynn/PDD/商品/2026-04-27/full_flow/卡彤网批-001 --publish

    # 批量发布当天所有商品
    python pdd_listing.py --date 2026-04-27 --publish

    # 首次运行：会打开浏览器，等待扫码登录
    python pdd_listing.py --input /path/to/product --publish
"""

import os
import sys
import json
import re
import time
import argparse
import asyncio
from pathlib import Path
from datetime import datetime

# ── 引入 Playwright ──────────────────────────────────
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 需要 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# ── 常量 ─────────────────────────────────────────────
OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")
STATE_FILE = os.path.expanduser("~/.hermes/pdd_seller_state.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# PDD 后端地址
PDD_BASE = "https://mms.pinduoduo.com"
PDD_LOGIN = f"{PDD_BASE}/login"
PDD_GOODS_ADD = f"{PDD_BASE}/goods/add"

# 超时（毫秒）
TIMEOUT = 30000
LONG_TIMEOUT = 60000


# ===================== 日志 ===========================

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌", "ACTION": "🖱️"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


# ===================== 登录模块 =======================

async def ensure_logged_in(page, headless: bool = False) -> bool:
    """确保已登录PDD商家后台。返回 True 如果已登录。"""
    # 无论是否有 STATE_FILE，先导航到商品发布页验证 session
    log("验证登录状态...", "INFO")
    await page.goto(PDD_GOODS_ADD, timeout=TIMEOUT, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # 判断是否已经在登录页（session 过期）
    if "login" in page.url.lower():
        if os.path.exists(STATE_FILE):
            log("已保存的登录状态已过期，需要重新扫码登录", "WARN")
        else:
            log("需要登录拼多多商家后台", "STEP")
        log("请在打开的浏览器中扫码登录", "ACTION")

        # 等待用户扫码并跳转
        max_wait = 300  # seconds
        start = time.time()
        while time.time() - start < max_wait:
            current_url = page.url
            if "login" not in current_url.lower():
                log(f"登录成功！跳转到: {current_url[:80]}", "OK")
                # 保存 storage state
                await _save_state(page)
                return True

            # 检查是否有操作验证（滑块验证等）
            page_content = await page.content()
            if "滑块" in page_content or "验证" in page_content:
                log("检测到滑块验证，请完成验证", "WARN")

            await page.wait_for_timeout(2000)

        log("扫码超时，请重新运行脚本", "ERR")
        return False
    else:
        log("已登录状态", "OK")
        return True


async def _save_state(page):
    """保存浏览器 storage state 到文件"""
    try:
        state = await page.context.storage_state()
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        log(f"登录状态已保存到 {STATE_FILE}", "OK")
    except Exception as e:
        log(f"保存登录状态失败: {e}", "WARN")


async def _load_state(browser) -> "BrowserContext":
    """从文件加载 storage state 创建context"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        context = await browser.new_context(
            storage_state=state,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return context
    else:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return context


# ===================== 页面辅助 =======================

async def wait_and_type(page, text: str, value: str, timeout: int = TIMEOUT):
    """按文本查找输入框并输入"""
    try:
        locator = page.get_by_placeholder(text)
        if await locator.count() > 0:
            await locator.first.fill(value, timeout=timeout)
            log(f"输入 [{value[:30]}...] 到 placeholder={text}", "ACTION")
            return True
    except Exception:
        log(f"wait_and_type: placeholder方式失败: {text}", "WARN")
    try:
        locator = page.locator(f'input[type="text"][placeholder*="{text}"]')
        if await locator.count() > 0:
            await locator.first.fill(value)
            return True
    except Exception:
        log(f"wait_and_type: input[placeholder]方式失败: {text}", "WARN")
    # 标签查找
    try:
        label = page.get_by_text(text, exact=False)
        if await label.count() > 0:
            # 找附近的input
            input_el = label.locator("xpath=../following-sibling::td//input | xpath=following::input[1]")
            if await input_el.count() > 0:
                await input_el.first.fill(value)
                return True
    except Exception:
        log(f"wait_and_type: 标签查找方式失败: {text}", "WARN")
    log(f"未找到输入框: {text}", "WARN")
    return False


async def wait_and_click(page, text: str, timeout: int = TIMEOUT):
    """按文本查找元素并点击"""
    try:
        # Try get_by_text first (most robust)
        locator = page.get_by_text(text, exact=False)
        if await locator.count() > 0:
            await locator.first.click(timeout=timeout)
            return True
    except Exception:
        log(f"wait_and_click: get_by_text方式失败: {text}", "WARN")
    try:
        # Try role button
        locator = page.get_by_role("button", name=text)
        if await locator.count() > 0:
            await locator.first.click(timeout=timeout)
            return True
    except Exception:
        log(f"wait_and_click: get_by_role方式失败: {text}", "WARN")
    log(f"未找到可点击元素: {text}", "WARN")
    return False


async def select_option_by_text(page, selector_label: str, option_text: str):
    """从下拉选择器选择选项"""
    try:
        # 找包含selector_label的div或span，然后找内部的下拉或select
        parent = page.locator(f'text={selector_label}').locator('..')
        if await parent.count() > 0:
            select = parent.locator('select, [role="combobox"], [class*="select"]')
            if await select.count() > 0:
                await select.first.click()
                await page.wait_for_timeout(500)
                # 选择选项
                option = page.get_by_text(option_text, exact=True)
                if await option.count() > 0:
                    await option.first.click()
                    return True
    except Exception:
        log(f"select_option_by_text 失败: {selector_label} / {option_text}", "WARN")
    log(f"未找到选择器: {selector_label} / {option_text}", "WARN")
    return False


async def upload_images(page, image_paths: list, upload_area_text: str = ""):
    """上传图片：触发file chooser事件"""
    if not image_paths:
        log("没有图片需要上传", "INFO")
        return 0

    # 过滤不存在的文件
    valid_paths = [p for p in image_paths if os.path.isfile(p)]
    if not valid_paths:
        log(f"所有图片文件都不存在，跳过上传", "WARN")
        return 0
    if len(valid_paths) < len(image_paths):
        log(f"{len(image_paths)-len(valid_paths)} 张图片不存在", "WARN")

    uploaded = 0
    for img_path in valid_paths:
        try:
            # 设置file chooser监听
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                # 触发上传按钮 - 找图片上传区域
                if upload_area_text:
                    btn = page.get_by_text(upload_area_text)
                else:
                    btn = page.locator('[class*="upload"], button:has-text("上传"), div:has-text("上传图片")').first
                if await btn.count() > 0:
                    await btn.first.click()
                else:
                    # 直接找input[type=file]
                    file_input = page.locator('input[type="file"]').first
                    if await file_input.count() > 0:
                        await file_input.set_input_files(img_path)
                        log(f"上传图片: {os.path.basename(img_path)}", "ACTION")
                        uploaded += 1
                        await page.wait_for_timeout(1000)
                        continue
                    else:
                        log(f"找不到上传按钮来上传: {os.path.basename(img_path)}", "WARN")
                        continue

            file_chooser = await fc_info.value
            await file_chooser.set_files(img_path)
            log(f"上传图片: {os.path.basename(img_path)}", "ACTION")
            uploaded += 1
            await page.wait_for_timeout(1500)  # 等待上传完成
        except Exception as e:
            log(f"上传失败 {os.path.basename(img_path)}: {e}", "WARN")

    return uploaded


# ===================== 页面操作：填写商品信息 =========

async def fill_title(page, listing: dict):
    """填写商品标题"""
    title = listing.get("goods_name", "")
    if not title:
        log("标题为空", "WARN")
        return
    # 找标题输入框，不同页面可能有不同实现
    success = await wait_and_type(page, "请输入商品标题", title)
    if not success:
        success = await wait_and_type(page, "商品标题", title)
    if not success:
        success = await wait_and_type(page, "标题", title)
    if success:
        log(f"标题已填写: {title[:30]}...", "OK")


async def fill_category(page, listing: dict):
    """填写商品分类"""
    cat_id = listing.get("cat_id")
    if cat_id:
        log(f"使用指定分类ID: {cat_id}", "INFO")
        # 如果有分类ID，尝试通过分类选择器设置
        return

    # 分类为 null — 尝试搜索/热门分类
    goods_name = listing.get("goods_name", "")
    log("尝试自动选择分类...", "STEP")

    # 猜分类关键词
    category_hints = {
        "女装": ["女装", "女士", "妈妈", "中老年"],
        "套装": ["套装", "两件套", "三件套"],
        "上衣": ["上衣", "T恤", "衬衫", "雪纺衫", "冰丝"],
        "裤子": ["裤", "阔腿裤", "打底裤"],
        "连衣裙": ["连衣裙", "裙子", "旗袍"],
        "外套": ["外套", "大衣", "开衫"],
    }

    chosen_category = "女装"  # 默认
    for cat, keywords in category_hints.items():
        if any(kw in goods_name for kw in keywords):
            chosen_category = cat
            break

    # 尝试选择分类
    try:
        # 点击分类选择器
        cat_selectors = [
            page.locator('[class*="category"]'),
            page.locator('[class*="cat"]'),
            page.locator('text=请选择商品分类'),
            page.locator('text=选择分类'),
        ]
        for sel in cat_selectors:
            if await sel.count() > 0:
                await sel.first.click()
                await page.wait_for_timeout(1000)
                break

        # 搜索分类
        search_input = page.locator('input[placeholder*="搜索"]').first
        if await search_input.count() > 0:
            await search_input.fill(chosen_category)
            await page.wait_for_timeout(1000)
            # 点击搜索结果
            result = page.locator(f'text={chosen_category}').first
            if await result.count() > 0:
                await result.click()
                log(f"分类已选择: {chosen_category}", "OK")
                return

        # 尝试从热门分类中点击
        hot_cats = page.locator('[class*="hot"]:has-text("女装"), [class*="popular"]')
        if await hot_cats.count() > 0:
            await hot_cats.first.click()
            await page.wait_for_timeout(1000)
            # 找子分类
            sub = page.get_by_text("上衣", exact=False).first
            if await sub.count() > 0:
                await sub.click()
                log("分类已选择: 女装 > 上衣", "OK")
                return

        log(f"分类选择可能需要手动操作 (期望: {chosen_category})", "WARN")
    except Exception as e:
        log(f"分类选择异常: {e}", "WARN")


async def fill_price(page, listing: dict):
    """填写价格"""
    goods_price = listing.get("goods_price", 0)  # 分
    market_price = listing.get("market_price", 0)  # 分

    price_yuan = goods_price / 100 if goods_price else 0
    # 如果划线价小于售价（单位错误），自动计算
    if market_price <= goods_price:
        market_price = int(goods_price * 1.5)
    market_yuan = market_price / 100 if market_price else price_yuan * 1.5

    # 销售价
    success = await wait_and_type(page, "请输入商品价格", f"{price_yuan:.2f}")
    if not success:
        success = await wait_and_type(page, "商品价格", f"{price_yuan:.2f}")
    if not success:
        success = await wait_and_type(page, "价格", f"{price_yuan:.2f}")
    if success:
        log(f"售价已填写: ¥{price_yuan:.1f}", "OK")

    # 划线价
    success = await wait_and_type(page, "请输入划线价", f"{market_yuan:.2f}")
    if not success:
        success = await wait_and_type(page, "划线价", f"{market_yuan:.2f}")
    if success:
        log(f"划线价已填写: ¥{market_yuan:.1f}", "OK")


async def fill_stock(page, listing: dict):
    """填写总库存"""
    total_stock = listing.get("goods_number", 100)
    success = await wait_and_type(page, "请输入库存", str(total_stock))
    if not success:
        success = await wait_and_type(page, "库存", str(total_stock))
    if success:
        log(f"总库存已填写: {total_stock}", "OK")


COLOR_KEYWORDS = ["色", "黑", "白", "红", "蓝", "黄", "绿", "粉", "紫", "灰", "咖", "米", "杏", "驼", "橘", "橙", "棕", "青", "银", "金", "玫", "肉"]
COLOR_NAMES = [
    "黑色", "白色", "红色", "蓝色", "黄色", "绿色", "粉色", "紫色", "灰色",
    "咖啡色", "卡其色", "米色", "杏色", "驼色", "橘色", "橙色", "棕色",
    "青色", "银色", "金色", "玫红", "肉色", "宝蓝", "酒红", "藏青",
    "军绿", "墨绿", "天蓝", "深蓝", "浅蓝", "深灰", "浅灰", "烟灰",
    "西瓜红", "中国红", "大红", "枣红", "豆沙", "藕粉", "香槟",
    "黑", "白", "红", "蓝", "黄", "绿", "粉", "紫", "灰", "米", "杏",
]

def _looks_like_color(text: str) -> bool:
    """判断文本是否看起来像颜色名"""
    if not text:
        return False
    # 直接匹配颜色名列表
    if text in COLOR_NAMES:
        return True
    # 包含"色"字
    if "色" in text and len(text) <= 6:
        return True
    # 包含常见颜色字符
    if any(c in text for c in ["黑", "白", "红", "蓝", "黄", "绿", "粉", "紫", "灰", "咖", "米", "杏", "驼"]):
        if len(text) <= 8:  # 颜色名通常很短
            return True
    return False

def _extract_color_name(raw: str) -> str:
    """从原始文本中提取颜色名"""
    if not raw:
        return ""
    # 如果直接在颜色名列表中
    if raw in COLOR_NAMES:
        return raw
    # 尝试在已知颜色名中匹配最长前缀
    matched = ""
    for cname in sorted(COLOR_NAMES, key=len, reverse=True):
        if raw.startswith(cname):
            matched = cname
            break
    if matched:
        return matched
    # 最后尝试：取第一个"色"字前的内容
    idx = raw.find("色")
    if idx > 0 and idx <= 4:
        return raw[:idx+1]
    # 实在不行，取前2个字
    if len(raw) > 4:
        return raw[:2]
    return raw


async def fill_sku(page, listing: dict):
    """填写SKU规格和价格库存"""
    sku_list = listing.get("sku_list", [])
    if not sku_list:
        log("无SKU数据，跳过", "INFO")
        return

    log(f"需要填写 {len(sku_list)} 个SKU", "STEP")

    # 解析颜色和尺码
    colors = set()
    sizes = set()
    for sku in sku_list:
        spec = sku.get("spec", "")
        parts = spec.split(",")
        if len(parts) >= 2:
            color_raw = parts[0].strip()
            size_raw = parts[1].strip()
            # 清理颜色字段：只取前2-3个中文颜色字
            color_clean = _extract_color_name(color_raw)
            if color_clean:
                colors.add(color_clean)
            if size_raw:
                sizes.add(size_raw)
        elif len(parts) == 1:
            spec_clean = parts[0].strip()
            if _looks_like_color(spec_clean):
                colors.add(spec_clean)
            else:
                sizes.add(spec_clean)

    colors = sorted(colors) if colors else []
    sizes = sorted(sizes) if sizes else []

    log(f"检测到颜色: {colors}", "INFO")
    log(f"检测到尺码: {sizes}", "INFO")

    try:
        # 先看看是否有"添加规格"按钮
        add_spec_btn = page.locator('button:has-text("添加规格"), button:has-text("规格")').first
        if await add_spec_btn.count() > 0:
            await add_spec_btn.click()
            await page.wait_for_timeout(1000)

        # 规格1：颜色
        if colors:
            # 找规格输入框，添加颜色
            spec_input = page.locator('input[placeholder*="规格"], input[placeholder*="颜色"]').first
            if await spec_input.count() > 0:
                for color in colors:
                    await spec_input.fill(color)
                    await page.wait_for_timeout(300)
                    # 按回车确认
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(300)
                log(f"颜色规格已添加: {colors}", "OK")

        # 规格2：尺码
        if sizes:
            size_input = page.locator('input[placeholder*="规格"]').last
            if await size_input.count() > 0:
                for size in sizes:
                    await size_input.fill(size)
                    await page.wait_for_timeout(300)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(300)
                log(f"尺码规格已添加: {sizes}", "OK")

        # 等待SKU表格生成，然后填入价格和库存
        await page.wait_for_timeout(2000)

        # 遍历每个SKU，在表格中找到对应的行填入价格和库存
        # PDD的SKU表格通常有价格和库存输入框
        sku_table = page.locator('table, [class*="sku"], [class*="table"], [class*="spec"]').first
        if await sku_table.count() > 0:
            # 尝试通过SKU表格填入
            for idx, sku in enumerate(sku_list):
                sku_price = sku.get("price", 0) / 100  # 转元
                sku_qty = sku.get("quantity", 10)

                # 尝试定位到该SKU行的价格输入框
                row = sku_table.locator(f'text={sku["spec"]}').locator('..')
                if await row.count() > 0:
                    cells = row.locator('input[type="text"]')
                    count = await cells.count()
                    if count >= 2:
                        await cells.nth(0).fill(f"{sku_price:.2f}")
                        await cells.nth(1).fill(str(sku_qty))
                        log(f"SKU {sku['spec']}: ¥{sku_price:.1f} x{sku_qty}", "ACTION")
                else:
                    log(f"未找到SKU行: {sku['spec']}", "WARN")
        else:
            log("未检测到SKU表格，尝试通用方式", "INFO")
            # 通用方式：按 spec 文本逐行匹配每个 SKU
            for sku in sku_list:
                sku_price = sku.get("price", 0) / 100
                sku_qty = sku.get("quantity", 10)
                spec_text = sku.get("spec", "")
                # 尝试找包含 spec 文本的行，然后填价格和库存
                if spec_text:
                    row = page.locator(f'text={spec_text}').locator('..')
                    if await row.count() > 0:
                        cells = row.locator('input[type="text"]')
                        count = await cells.count()
                        if count >= 2:
                            await cells.nth(0).fill(f"{sku_price:.2f}")
                            await cells.nth(1).fill(str(sku_qty))
                            log(f"SKU {spec_text}: ¥{sku_price:.1f} x{sku_qty}", "ACTION")
                            continue
                # 回退：按行号顺序匹配（假设 input 排序与 sku_list 一致）
                row_inputs = page.locator('input[type="text"]:visible')
                input_count = await row_inputs.count()
                sku_idx = sku_list.index(sku)
                if sku_idx >= 0 and (sku_idx * 2 + 1) < input_count:
                    await row_inputs.nth(sku_idx * 2).fill(f"{sku_price:.2f}")
                    await row_inputs.nth(sku_idx * 2 + 1).fill(str(sku_qty))
                    log(f"SKU #{sku_idx} (fallback): ¥{sku_price:.1f} x{sku_qty}", "ACTION")
                else:
                    log(f"未找到输入框匹配 SKU: {spec_text}", "WARN")
            log(f"SKU 价格库存填写完成", "INFO")

    except Exception as e:
        log(f"SKU填写异常: {e}", "WARN")


async def fill_delivery(page):
    """填写发货时间（默认48h）"""
    try:
        # 找发货时间选项
        delivery_label = page.locator('text=发货时间, text=发货, text=配送').first
        if await delivery_label.count() > 0:
            await delivery_label.click()
            await page.wait_for_timeout(500)
            # 选48h
            option = page.locator('text=48小时, text=2天').first
            if await option.count() > 0:
                await option.click()
                log("发货时间已设置: 48小时", "OK")
                return

        # 尝试下拉选择
        selectors = [
            page.locator('[class*="delivery"]'),
            page.locator('[class*="ship"]'),
        ]
        for sel in selectors:
            if await sel.count() > 0:
                await sel.first.click()
                await page.wait_for_timeout(500)
                option = page.get_by_text("48").first
                if await option.count() > 0:
                    await option.click()
                    log("发货时间已设置: 48小时", "OK")
                    return

        log("发货时间设置可能需要手动操作", "WARN")
    except Exception as e:
        log(f"设置发货时间异常: {e}", "WARN")


async def fill_weight(page):
    """填写重量（默认0.5kg）"""
    try:
        success = await wait_and_type(page, "请输入重量", "0.5")
        if not success:
            success = await wait_and_type(page, "重量", "0.5")
        if not success:
            success = await wait_and_type(page, "kg", "0.5")
        if success:
            log("重量已设置: 0.5kg", "OK")
    except Exception as e:
        log(f"设置重量异常: {e}", "WARN")


async def save_or_submit(page, publish: bool = False):
    """保存草稿或提交"""
    if publish:
        # 找提交/发布按钮
        submit_btns = [
            page.locator('button:has-text("提交")'),
            page.locator('button:has-text("发布")'),
            page.locator('button:has-text("上架")'),
            page.locator('[class*="submit"]'),
            page.locator('[class*="publish"]'),
        ]
        for btn in submit_btns:
            if await btn.count() > 0 and await btn.first.is_visible():
                await btn.first.click()
                log("已点击提交按钮", "ACTION")
                await page.wait_for_timeout(3000)
                return True
        log("未找到提交按钮", "WARN")
        return False
    else:
        # 保存草稿
        draft_btns = [
            page.locator('button:has-text("草稿")'),
            page.locator('button:has-text("暂存")'),
            page.locator('button:has-text("保存")'),
        ]
        for btn in draft_btns:
            if await btn.count() > 0 and await btn.first.is_visible():
                await btn.first.click()
                log("已保存草稿", "OK")
                await page.wait_for_timeout(2000)
                return True
        log("未找到保存按钮", "WARN")
        return False


# ===================== 发布单个商品 ===================

def preview_listing(listing: dict):
    """预览模式：打印将填写的表单摘要"""
    goods_name = listing.get("goods_name", "")
    goods_price = listing.get("goods_price", 0)
    market_price = listing.get("market_price", 0)
    goods_number = listing.get("goods_number", 0)
    main_images = listing.get("main_images", [])
    detail_images = listing.get("detail_images", [])
    sku_list = listing.get("sku_list", [])
    remark = listing.get("remark", "")

    # 修正划价数据错误
    if market_price <= goods_price:
        market_price = int(goods_price * 1.5)

    print(f"  {'─'*40}")
    print(f"  📋 上架摘要 (预览模式)")
    print(f"  {'─'*40}")
    print(f"  标题:    {goods_name}")
    print(f"  售价:    ¥{goods_price/100:.2f}")
    print(f"  划线价:  ¥{market_price/100:.2f}")
    print(f"  总库存:  {goods_number} 件")
    print(f"  主图:    {len(main_images)} 张")
    print(f"  详情图:  {len(detail_images)} 张")
    print(f"  SKU数:   {len(sku_list)} 个")

    # 显示前5个SKU
    for sku in sku_list[:5]:
        print(f"    SKU: {sku['spec']:20s} ¥{sku['price']/100:.1f}  x{sku['quantity']}")
    if len(sku_list) > 5:
        print(f"    ... 还有 {len(sku_list)-5} 个SKU")

    print(f"  来源:    {remark[:50]}...")
    print(f"  {'─'*40}")

    # 检查图片是否存在
    missing = []
    for img in main_images + detail_images:
        if not os.path.isfile(img):
            missing.append(img)
    if missing:
        print(f"  ⚠️  {len(missing)} 张图片文件不存在:")
        for m in missing[:3]:
            print(f"     {os.path.basename(m)}")
    else:
        print(f"  ✅ 所有图片文件都存在")

    # 检查数据合理性
    print(f"")
    if goods_price <= 0:
        print(f"  ⚠️ 售价为0，数据可能不正确")
    if not goods_name:
        print(f"  ⚠️ 标题为空")
    if not main_images:
        print(f"  ⚠️ 没有主图")
    if not detail_images:
        print(f"  ⚠️ 没有详情图")
    print(f"")


async def publish_listing(page, listing: dict):
    """发布单个商品"""
    log("开始填写商品信息", "STEP")

    # 1. 标题
    await fill_title(page, listing)

    # 2. 分类
    await fill_category(page, listing)

    # 3. 上传主图
    main_images = [img for img in listing.get("main_images", []) if os.path.isfile(img)]
    log(f"上传 {len(main_images)} 张主图...", "STEP")
    if main_images:
        uploaded = await upload_images(page, main_images, "上传主图")
        log(f"主图上传完成: {uploaded}/{len(main_images)}", "OK" if uploaded == len(main_images) else "WARN")

    # 4. 上传详情图
    detail_images = [img for img in listing.get("detail_images", []) if os.path.isfile(img)]
    log(f"上传 {len(detail_images)} 张详情图...", "STEP")
    if detail_images:
        uploaded = await upload_images(page, detail_images, "上传详情图")
        log(f"详情图上传完成: {uploaded}/{len(detail_images)}", "OK" if uploaded == len(detail_images) else "WARN")

    # 5. 价格
    await fill_price(page, listing)

    # 6. 库存
    await fill_stock(page, listing)

    # 7. SKU
    await fill_sku(page, listing)

    # 8. 发货时间
    await fill_delivery(page)

    # 9. 重量
    await fill_weight(page)

    # 10. 截图保存当前填写状态
    try:
        await page.screenshot(path=os.path.join(os.path.dirname(STATE_FILE), f"listing_{int(time.time())}.png"))
        log("当前填写状态截图已保存", "INFO")
    except Exception:
        log("截图保存失败", "WARN")

    log("所有字段填写完成", "OK")


# ===================== 主流程 =========================

async def run(product_dirs: list, preview: bool = False, publish: bool = False):
    """主流程入口"""
    print(f"")
    print(f"  {'='*50}")
    print(f"  📤 拼多多自动上架工具")
    print(f"  模式: {'📋 预览' if preview else '🚀 发布'}")
    print(f"  商品: {len(product_dirs)} 个")
    print(f"  {'='*50}")

    # ── 加载每个商品的数据 ──
    listings = []
    for product_dir in product_dirs:
        listing_file = os.path.join(product_dir, "listing-ready", "listing.json")
        if not os.path.isfile(listing_file):
            # 也尝试直接读 listing.json
            listing_file = os.path.join(product_dir, "listing.json")
        if not os.path.isfile(listing_file):
            log(f"未找到 listing.json: {product_dir}", "ERR")
            continue

        try:
            with open(listing_file, "r", encoding="utf-8") as f:
                listing = json.load(f)
            dir_name = os.path.basename(product_dir)
            log(f"加载商品: {dir_name}", "OK")
            # 修复图片路径：如果图片路径是相对的，转绝对
            listing = _fix_image_paths(listing, product_dir)
            listings.append((product_dir, listing))
        except Exception as e:
            log(f"加载 listing.json 失败: {e}", "ERR")

    if not listings:
        log("没有可处理的商品", "ERR")
        return

    # ── 预览模式 ──
    if preview:
        for product_dir, listing in listings:
            dir_name = os.path.basename(product_dir)
            print(f"\n  📦 {dir_name}")
            preview_listing(listing)
        print(f"\n  {'='*50}")
        print(f"  ✅ 预览完成，共 {len(listings)} 个商品")
        print(f"  {'='*50}")
        return

    # ── 发布模式 ──
    if not publish:
        log("请指定 --publish 或 --preview", "INFO")
        return

    # 启动浏览器
    log("启动浏览器...", "STEP")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 首次需要扫码
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # 加载或新建 context
        context = await _load_state(browser)
        page = await context.new_page()

        # 处理登录
        logged_in = await ensure_logged_in(page)
        if not logged_in:
            await browser.close()
            return

        # 发布每个商品
        for idx, (product_dir, listing) in enumerate(listings):
            dir_name = os.path.basename(product_dir)
            print(f"\n  {'='*50}")
            print(f"  📦 {idx+1}/{len(listings)} {dir_name}")
            print(f"  {'='*50}")

            if idx > 0:
                # 非第一个商品，重新导航到发布页
                await page.goto(PDD_GOODS_ADD, timeout=TIMEOUT, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

            try:
                await publish_listing(page, listing)
                # 提交
                log("准备提交商品...", "STEP")
                submitted = await save_or_submit(page, publish=True)
                if submitted:
                    log(f"✅ 商品发布成功: {dir_name}", "OK")
                else:
                    log(f"⚠️ 商品可能未成功提交: {dir_name}", "WARN")
                # 等待页面处理
                await page.wait_for_timeout(3000)
            except Exception as e:
                log(f"发布失败 {dir_name}: {e}", "ERR")
                # 截图保存失败状态
                try:
                    await page.screenshot(path=f"/tmp/pdd_fail_{int(time.time())}.png")
                except Exception:
                    log("发布失败截图保存出错", "WARN")

        await context.close()
        await browser.close()

    print(f"\n  {'='*50}")
    print(f"  ✅ 全部完成")
    print(f"  {'='*50}")


def _fix_image_paths(listing: dict, product_dir: str) -> dict:
    """修复图片路径：确保图片路径是绝对路径"""
    for key in ["main_images", "detail_images"]:
        images = listing.get(key, [])
        fixed = []
        for img in images:
            if not os.path.isabs(img):
                img = os.path.join(product_dir, img)
            if not os.path.isfile(img):
                # 尝试从 listing-ready/ 目录找
                alt = os.path.join(product_dir, "listing-ready", os.path.basename(img))
                if os.path.isfile(alt):
                    img = alt
            fixed.append(img)
        listing[key] = fixed
    return listing


def find_product_dirs(date_str: str = None, input_path: str = None):
    """查找商品目录（去重）"""
    if input_path:
        if os.path.isfile(input_path):
            input_path = os.path.dirname(input_path)
        return [input_path]

    if date_str:
        base = os.path.join(OUTPUT_ROOT, date_str)
        if not os.path.isdir(base):
            log(f"日期目录不存在: {base}", "ERR")
            return []

        # 搜索所有含有 listing-ready/listing.json 的目录，去重
        seen_dirs = set()
        dirs = []
        for root, dirs_here, files in os.walk(base):
            if "listing-ready" in dirs_here:
                dpath = root
                # 通过商品名去重（取目录名，如"卡彤网批-001"）
                dir_name = os.path.basename(dpath)
                if dir_name not in seen_dirs:
                    seen_dirs.add(dir_name)
                    dirs.append(dpath)
                # 不要递归进 listing-ready 里面
                dirs_here.remove("listing-ready")

        # 按目录名排序
        dirs.sort(key=lambda d: os.path.basename(d))
        return dirs

    return []


# ===================== CLI入口 ========================

def main():
    parser = argparse.ArgumentParser(
        description="拼多多商家后台自动上架工具 — 登录+填表+提交",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览
  python pdd_listing.py --input /home/pebynn/PDD/商品/2026-04-27/full_flow/卡彤网批-001 --preview

  # 发布单个
  python pdd_listing.py --input /home/pebynn/PDD/商品/2026-04-27/full_flow/卡彤网批-001 --publish

  # 批量发布当天所有
  python pdd_listing.py --date 2026-04-27 --publish
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", "-i", type=str, help="商品目录路径（或 listing.json 路径）")
    group.add_argument("--date", "-d", type=str, help="日期文件夹，如 2026-04-27")

    parser.add_argument("--preview", action="store_true", help="预览模式：只输出表单摘要，不打开浏览器")
    parser.add_argument("--publish", action="store_true", help="发布模式：实际打开浏览器并填写提交")
    parser.add_argument("--headless", action="store_true", help="使用headless模式（仅publish模式有效，首次登录仍需界面）")

    args = parser.parse_args()

    if not args.input and not args.date:
        # 默认使用当天日期
        args.date = time.strftime("%Y-%m-%d")
        log(f"未指定 --input 或 --date，默认使用当天: {args.date}", "INFO")

    # 查找商品目录
    product_dirs = find_product_dirs(args.date, args.input)
    if not product_dirs:
        log(f"没有找到包含 listing.json 的商品目录", "ERR")
        sys.exit(1)

    log(f"找到 {len(product_dirs)} 个商品", "OK")
    for d in product_dirs:
        log(f"  {os.path.basename(d)}", "INFO")

    # 执行
    asyncio.run(run(product_dirs, preview=args.preview, publish=args.publish))


if __name__ == "__main__":
    main()

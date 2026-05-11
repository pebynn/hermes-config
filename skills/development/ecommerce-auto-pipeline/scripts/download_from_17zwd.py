#!/usr/bin/env python3
"""
17网供销版（cs.17zwd.com）商品图片批量下载工具 v3.0
改用 Playwright（替代 Selenium），解决以下问题：
  ✅ React SPA 原生支持 — Playwright 内置 auto-wait，不需要 time.sleep 猜加载
  ✅ Ant Design 复选框 — locator.check() 自动处理覆盖层拦截
  ✅ 下载拦截 — page.expect_download() 原生捕获 ZIP，不依赖 .crdownload 监控
  ✅ 网络空闲检测 — wait_until="networkidle" 精确等待 React 渲染完成
  ✅ 自带 Chromium — 不需要额外安装 ChromeDriver
  ✅ stealth 加持 — playwright-stealth 绕过反爬检测

用法：
    # 单个商品（默认输出到 /home/pebynn/PDD/商品/当天日期/）
    python download_from_17zwd.py --goods-id 155155280 --username 17825029430 --password 17825029430

    # 批量（从候选列表JSON）
    python download_from_17zwd.py --candidates ./candidates.json --username 17825029430 --password 17825029430

    # 调试模式（非headless + 截图）
    python download_from_17zwd.py --goods-id 155155280 --debug --username 17825029430 --password 17825029430

    # 自动解压
    python download_from_17zwd.py --candidates ./candidates.json --output ./zips --extract-to ./images --username 17825029430 --password 17825029430
"""

import os
import sys
import json
import re
import time
import argparse
import zipfile
import glob
import asyncio
from pathlib import Path

# ===================== 依赖检查 =====================

try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
except ImportError:
    print("❌ 需要 playwright: pip install playwright")
    print("   还需要浏览器: playwright install chromium")
    sys.exit(1)

# playwright-stealth 可选，用于绕过反爬
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False


# ===================== 配置 =====================

BASE_URL = "https://cs.17zwd.com"
LOGIN_URL = "https://pp.17zwd.com/login?redirectUrl=https://cs.17zwd.com/"

# 超时配置（毫秒）
NAVIGATION_TIMEOUT = 45_000     # 页面导航超时
WAIT_ELEMENT_TIMEOUT = 30_000   # 元素等待超时
WAIT_PACK_TIMEOUT = 70_000      # 等待打包超时
CLICK_DELAY = 1500              # 点击后等待（毫秒）


# ===================== Playwright 下载器 =====================

class Downloader17zwd:
    """17网供销版商品图片下载器（Playwright版）"""

    def __init__(self, download_dir, headless=True, username=None,
                 password=None, debug=False):
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)
        self.headless = headless
        self.username = username
        self.password = password
        self.debug = debug
        self.browser = None
        self.context = None
        self.page = None
        self.success_count = 0
        self.fail_count = 0
        self._download_promise = None  # 当前商品的下载追踪

    # ---------- 生命周期 ----------

    async def start(self):
        """启动浏览器"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            # 自动下载到指定目录，不弹对话框
            accept_downloads=True,
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(WAIT_ELEMENT_TIMEOUT)

        # 可选：stealth 反爬
        if HAS_STEALTH:
            await stealth_async(self.page)

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None

    # ---------- 调试 ----------

    async def _debug(self, step_name):
        """调试：截图保存"""
        if not self.debug:
            return
        safe = step_name.replace(" ", "_").replace("/", "_")
        path = os.path.join(self.download_dir, f"debug_{safe}.png")
        try:
            await self.page.screenshot(path=path, full_page=True)
            print(f"  📸 截图: {path}")
        except Exception as e:
            print(f"  ⚠️ 截图失败: {e}")

    # ---------- 登录 ----------

    async def login(self):
        """登录17网（使用Playwright原生fill）"""
        if not self.username or not self.password:
            print("  ⚠️ 未提供登录凭证，跳过登录")
            return False

        print(f"  🔑 登录17网...")
        page = self.page

        # 导航到登录页
        await page.goto(LOGIN_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Playwright 的 fill() 自动触发 React input 事件
        await page.fill('input[name="username"]', self.username)
        await page.wait_for_timeout(300)
        await page.fill('input[name="password"]', self.password)
        await page.wait_for_timeout(300)

        # 点击登录按钮
        await page.click('button:has-text("登录")', timeout=WAIT_ELEMENT_TIMEOUT)
        print(f"    ✔ 已点击登录按钮")

        # 等待登录完成（跳转到 cs.17zwd.com）
        try:
            await page.wait_for_url("https://cs.17zwd.com/**", timeout=NAVIGATION_TIMEOUT)
            print(f"    ✅ 登录成功，当前: {page.url[:60]}")
            await page.wait_for_timeout(3000)
            return True
        except PwTimeout:
            # 尝试直接导航到cs首页验证
            await page.goto("https://cs.17zwd.com/", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            if "login" not in page.url and "cs.17zwd.com" in page.url:
                print(f"    ✅ 已登录，当前: {page.url[:60]}")
                return True
            print(f"    ⚠️ 登录可能失败（当前URL: {page.url[:60]}）")
            return False

    # ---------- 店铺信息提取 ----------

    async def _extract_shop_info(self):
        """从商品页提取店铺名称/地址/货号"""
        page = self.page
        info = {"shop_name": "", "shop_address": "", "goods_no": "", "price": 0, "title": ""}

        try:
            body = await page.locator("body").text_content()

            # 商品标题：取 <title> 标签
            try:
                page_title = await page.title()
                if page_title and "17" not in page_title[:3]:
                    # 17网 detail 页标题格式通常是 "商品名_17网"
                    clean = re.sub(r'[_\-|]\s*17.*|[_\-|]\s*拿货.*', '', page_title).strip()
                    if clean and len(clean) > 4:
                        info["title"] = clean
            except Exception:
                pass
            # 兜底：从 body 取 goodsTitle 类
            if not info["title"]:
                try:
                    title_el = page.locator('[class*="goodsTitle"]').first
                    if await title_el.is_visible(timeout=2000):
                        t = await title_el.text_content()
                        if t:
                            info["title"] = t.strip()
                except Exception:
                    pass
            # 二次兜底：从 body 文本找最长的连续商品描述
            if not info["title"]:
                for m in re.finditer(r'([\u4e00-\u9fff\w\s]{10,80})', body):
                    t = m.group(1).strip()
                    if any(k in t for k in ["款", "装", "套", "衫", "裤", "裙"]):
                        if len(t) > len(info["title"]):
                            info["title"] = t[:60]

            # 价格：找 goodsPrice 类
            try:
                price_el = page.locator('[class*="goodsPrice"]').first
                if await price_el.is_visible(timeout=2000):
                    price_text = await price_el.text_content()
                    price_match = re.search(r'[¥￥]?\s*(\d+(?:\.\d+)?)', price_text or "")
                    if price_match:
                        info["price"] = float(price_match.group(1))
            except Exception:
                pass
            # 兜底：从 body 文本找 ¥ 价格
            if not info["price"]:
                for m in re.finditer(r'[¥￥]\s*(\d+(?:\.\d+)?)', body):
                    p = float(m.group(1))
                    if 5 <= p <= 50:
                        info["price"] = p
                        break
            
            # SKU 规格：颜色 + 尺码
            info["sku"] = {"colors": [], "sizes": []}
            # 颜色分类（格式：颜色分类001 卡其色 002 黄色 或 颜色分类黑色 咖色）\n            # 取颜色分类到尺码分类之间的所有2-8字中文词
            colors_match = re.search(r'颜色分类[\s\d#]*?(.+?)(?:尺码分类|风格|款式|裙型|上市|宝贝|$)', body)
            if colors_match:
                raw = colors_match.group(1).strip()
                colors = re.findall(r'[\u4e00-\u9fff]{2,8}', raw)
                colors = [c for c in colors if '尺码' not in c and '分类' not in c]
                if 1 <= len(colors) <= 20:
                    info["sku"]["colors"] = colors
            # 尺码（格式：尺码分类L XL 2XL 3XL 4XL 或 颜色尺码S￥）
            sizes_section = re.search(r'尺码分类\s*([\w\s]{3,60}?)(?:风格|款式|裙型|上市|宝贝)', body)
            if not sizes_section:
                sizes_section = re.search(r'颜色尺码([\w]+?)￥', body)
            if sizes_section:
                raw = sizes_section.group(1).strip()
                sizes = re.split(r'\s+', raw)
                sizes = [s for s in sizes if re.match(r'^[\w#+\u4e00-\u9fff]{1,6}$', s)]
                if 1 <= len(sizes) <= 20:
                    info["sku"]["sizes"] = sizes
            # 打印SKU信息
            if info["sku"]["colors"] or info["sku"]["sizes"]:
                sku_parts = []
                if info["sku"]["colors"]:
                    c = info["sku"]["colors"]
                    sku_parts.append(f"🎨 {c[0]}{'...' if len(c) > 1 else ''}({len(c)}色)")
                if info["sku"]["sizes"]:
                    s = info["sku"]["sizes"]
                    sku_parts.append(f"📏 {s[0]}{'...' if len(s) > 1 else ''}({len(s)}码)")
                print(f"    {' | '.join(sku_parts)}")
            
            # 店铺名称：找"关注分享"前的店铺名，过滤地名词和前缀
            skip_words = ['小程序','微信','APP','公告','潮汕','广州','杭州','普宁','沙河','深圳','义乌','北京','上海','东莞','佛山','中山','您好']
            shop_candidates = []
            for m in re.finditer(r'([\u4e00-\u9fff]{2,12})\s*关注分享', body):
                s = m.group(1)
                # 去掉"小程序"等前缀
                for sw in ['小程序','微信','APP']:
                    s = s.replace(sw, '')
                if s and len(s) >= 2 and not any(x in s for x in skip_words):
                    shop_candidates.append(s)
            # 从公告里的【店名】提取
            for m in re.finditer(r'【([^】]{2,10})】', body):
                s = m.group(1)
                if not any(x in s for x in skip_words):
                    shop_candidates.append(s)
            
            if shop_candidates:
                info["shop_name"] = shop_candidates[0]
            
            # 货号：匹配"货号"后面5-12位编号，用后处理剔除日期
            for m in re.finditer(r'货号[\s:：]*([\w#\-+]{5,20})', body):
                raw = m.group(1).strip().rstrip('#-')
                # 去掉后面的日期时间部分（如 2025-06-11 02:47:56）
                clean = re.sub(r'20\d{2}[-/]\d{1,2}[-/]\d{1,2}.*', '', raw).strip()
                clean = re.sub(r'\s+\d{2}:\d{2}.*', '', clean).strip()
                if clean and "配货" not in clean and "预计" not in clean and 2 <= len(clean) <= 12:
                    info["goods_no"] = clean
                    break
            
            # 地址：找"地址："后面的内容（止于句号或"公告"）
            for m in re.finditer(r'地址[：:]\s*(.{5,80}?)(?:[。.公告]|\s+【)', body):
                info["shop_address"] = m.group(1).strip()
                break
            if not info["shop_address"]:
                for m in re.finditer(r'(?:地址[：:]\s*)([^\n]{5,60})', body):
                    info["shop_address"] = m.group(1).strip().rstrip('公告')
                    break

            parts = []
            if info["shop_name"]:
                parts.append(f"🏪 {info['shop_name']}")
            if info["shop_address"]:
                parts.append(f"📍 {info['shop_address']}")
            if info["goods_no"]:
                parts.append(f"🔖 货号: {info['goods_no']}")
            if info.get("price"):
                parts.append(f"💰 ¥{info['price']}")
            if info.get("title"):
                parts.append(f"📄 {info['title'][:30]}")
            if parts:
                print(f"    {' | '.join(parts)}")

        except Exception as e:
            print(f"    ⚠️ 店铺信息提取: {e}")

        return info

    # ---------- 元数据保存 ----------

    def _save_meta(self, zip_path, goods_url, shop_info):
        meta = {
            "source_url": goods_url,
            "download_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "shop_name": shop_info.get("shop_name", ""),
            "shop_address": shop_info.get("shop_address", ""),
            "goods_no": shop_info.get("goods_no", ""),
            "price": shop_info.get("price", 0),
            "title": shop_info.get("title", ""),
            "sku": shop_info.get("sku", {"colors": [], "sizes": []}),
        }
        meta_path = os.path.splitext(zip_path)[0] + "_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"    📝 元数据已保存: {os.path.basename(meta_path)}")

    # ---------- 核心：单个商品下载 ----------

    async def download_single(self, goods_url, retries=2):
        """
        下载单个商品所有图片。
        goods_url: 完整商品URL，如 cs.17zwd.com/item/{goods_id}
        返回 dict {"zip": zip路径, "shop_info": {...}} 或 None
        """
        print(f"\n  📥 {goods_url}")
        page = self.page

        for attempt in range(1, retries + 1):
            try:
                # ── 第1步：打开商品详情页 ──
                await page.goto(goods_url, wait_until="networkidle",
                                timeout=NAVIGATION_TIMEOUT)
                await page.wait_for_timeout(3000)
                print(f"    ✔ 页面加载完成")
                await self._debug("1_商品页")

                # ── 提取店铺信息 ──
                shop_info = await self._extract_shop_info()

                # ── 第2步：找「下载视频/图片」按钮 ──
                # cs.17zwd.com CSS Module 哈希 class，只能靠文本匹配
                download_btn = page.locator(
                    "text=下载视频/图片"
                ).first

                try:
                    await download_btn.wait_for(state="attached", timeout=5000)
                    await download_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await download_btn.click()
                    print(f"    ✔ 点击下载按钮")
                except Exception:
                    print(f"    ⚠️ 未找到下载按钮，跳过该商品")
                    await self._debug("error_无下载按钮")
                    self.fail_count += 1
                    return None
                await self._debug("2_点击下载后")

                # ── 第3步：等待 Ant Design Modal 弹窗 ──
                try:
                    await page.wait_for_selector(
                        ".ant-modal-content",
                        state="visible",
                        timeout=WAIT_ELEMENT_TIMEOUT,
                    )
                    print(f"    ✔ 下载弹窗弹出")
                except PwTimeout:
                    print(f"    ⚠️ 下载弹窗未弹出")
                    await self._debug("error_无弹窗")
                    self.fail_count += 1
                    return None
                await page.wait_for_timeout(1000)
                await self._debug("3_弹窗弹出")

                # ── 第4步：选择下载项（勾选主图 + 详情图） ──
                # ★ 注意：cs.17zwd.com 弹窗是 CSS Module 自定义组件，不是标准 Ant Design 复选框
                # 结构为：<div>（item）> 图标 + <span>主图下载</span> + <div class="checkWrap"><div>
                # 点击 item 父级 div 切换选中状态
                modal = page.locator(".ant-modal-content")
                
                # 找到所有可点击的下载项（排除 disabled 的）
                items = modal.locator("div:not([class*='disabled'])").filter(has_text="下载")
                
                # 点击「主图下载」项
                main_item = modal.locator("text=主图下载").first
                if await main_item.is_visible():
                    await main_item.click()
                    print(f"    ✔ 选中: 主图下载")
                await page.wait_for_timeout(300)
                
                # 点击「详情图下载」项
                detail_item = modal.locator("text=详情图下载").first
                if await detail_item.is_visible():
                    await detail_item.click()
                    print(f"    ✔ 选中: 详情图下载")
                await page.wait_for_timeout(300)

                await self._debug("4_选中下载项后")
                
                # ── 第5步：点击「立即下载」并捕获下载 ──
                # ★ 注意：「立即下载」是 <div> 不是 <button>！
                # ── 第5步：点击「立即下载」→ 等待打包 → 点击「下载」──
                # ★ 注意：点击「立即下载」后，弹窗内容整个替换为进度视图：
                #   [打包中 20%  下载] → [打包完成 100% 下载]
                # 「下载」按钮是新出现的，class 和文本都和之前不同
                submit_btn = modal.locator("text=立即下载").first
                
                if not await submit_btn.is_visible():
                    print(f"    ⚠️ 提交按钮不可见")
                    await self._debug("error_无提交按钮")
                    self.fail_count += 1
                    return None

                # 第1次点击：提交打包请求
                await submit_btn.click()
                print(f"    ✔ 提交下载请求，等待服务端打包...")
                await page.wait_for_timeout(1000)

                # 等待打包完成（弹窗内容变化为进度视图）
                try:
                    # 方式1：检测进度文本
                    await page.wait_for_function(
                        """
                        () => {
                            const modal = document.querySelector('.ant-modal-content');
                            if (!modal) return false;
                            const text = modal.textContent || '';
                            return text.includes('打包完成') || text.includes('100%');
                        }
                        """,
                        timeout=WAIT_PACK_TIMEOUT,
                    )
                    print(f"    ✔ 打包完成")
                except PwTimeout:
                    print(f"    ⚠️ 打包状态检测超时，继续尝试下载...")

                await page.wait_for_timeout(1000)
                
                # 弹窗内容已替换！现在找新出现的「下载」按钮
                # 设置下载监听器，拦截即将触发的ZIP下载
                async with page.expect_download(timeout=60000) as download_info:
                    # 找新按钮：文本为"下载"（不是"立即下载"）
                    download_new = modal.locator("text=下载").first
                    
                    # 等待新按钮可点击
                    await download_new.wait_for(state="visible", timeout=10000)
                    print(f"    ✔ 点击下载按钮")
                    await download_new.click()
                    
                    # 如果第一次没触发，再试一次
                    await page.wait_for_timeout(2000)
                    if await download_new.is_visible():
                        await download_new.click()
                
                    # 获取下载文件
                    download = await download_info.value
                    suggested = download.suggested_filename or f"goods_{int(time.time())}.zip"
                    zip_path = os.path.join(self.download_dir, suggested)
                    if os.path.exists(zip_path):
                        base, ext = os.path.splitext(suggested)
                        zip_path = os.path.join(self.download_dir, f"{base}_{int(time.time())}{ext}")
                    await download.save_as(zip_path)
                    
                    size_kb = os.path.getsize(zip_path) / 1024
                    print(f"    ✅ 下载成功: {os.path.basename(zip_path)} ({size_kb:.1f}KB)")
                    self._save_meta(zip_path, goods_url, shop_info)
                    self.success_count += 1
                    return {"zip": zip_path, "shop_info": shop_info}

            except PwTimeout as e:
                print(f"    ⚠️ 超时 (尝试 {attempt}/{retries})")
                await self._debug(f"error_超时_{attempt}")
            except Exception as e:
                print(f"    ⚠️ 未知错误 (尝试 {attempt}/{retries}): {e}")
                await self._debug(f"error_{attempt}")

            # 重试：刷新页面
            await page.wait_for_timeout(2000)

        return None

    # ---------- 批量下载 ----------

    async def batch_download(self, urls):
        print(f"\n{'='*50}")
        print(f"📥 17网商品批量下载（Playwright）")
        print(f"  共 {len(urls)} 个商品")
        print(f"  下载目录: {self.download_dir}")
        print(f"{'='*50}")

        results = []
        for i, url in enumerate(urls):
            print(f"\n--- [{i + 1}/{len(urls)}] ---")
            result = await self.download_single(url)
            if result:
                results.append(result)
            else:
                results.append({"url": url, "zip": None, "shop_info": {}})
            await self.page.wait_for_timeout(2000)

        print(f"\n{'='*50}")
        print(f"📊 下载统计")
        print(f"  成功: {self.success_count} / {len(urls)}")
        print(f"  失败: {self.fail_count}")
        print(f"{'─'*50}")
        for r in results:
            if r.get("zip") and r.get("shop_info"):
                s = r["shop_info"]
                name = s.get("shop_name", "?") or "?"
                gno = s.get("goods_no", "?") or "?"
                print(f"  ✅ {os.path.basename(r['zip'])}  ← {name} / 货号: {gno}")
            elif r.get("zip"):
                print(f"  ✅ {os.path.basename(r['zip'])}")
        print(f"{'='*50}")
        return results

    # ---------- 解压 ----------


    def _write_shop_marker(self, target_dir, shop_info):
        content = f"""========================================
    📦 商品来源信息（17网供销版-后台管理专用）
    ========================================
    店铺名称: {shop_info.get('shop_name', '未知')}
    店铺地址: {shop_info.get('shop_address', '未知')}
    商品货号: {shop_info.get('goods_no', '未知')}
    来源URL: {shop_info.get('source_url', '未知')}
    下载时间: {shop_info.get('download_time', '未知')}
    ========================================

    ⚠️ 此信息仅用于商品管理后台，不可面向客户展示！

    上架到拼多多后，在「商品管理」→ 编辑商品：
    ✅ 「商家编码」→ 填入货号（客户不可见）
    ✅ 「商品备注」→ 填入店铺名称+地址（客户不可见）
    ❌ 不要写入标题、描述、主图等客户可见区域
    ========================================
    """
        info_path = os.path.join(target_dir, "货源信息.txt")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(content)


    def extract_all_zips(self, target_dir=None):
        """解压目录下所有ZIP，解压后清理ZIP、meta JSON、清单
        目录名格式：店铺名称-货号（从meta JSON读取）"""
        if not target_dir:
            target_dir = self.download_dir
        os.makedirs(target_dir, exist_ok=True)

        extracted = 0
        for f in os.listdir(self.download_dir):
            if not f.endswith(".zip"):
                continue
            zip_path = os.path.join(self.download_dir, f)
            base = os.path.splitext(f)[0]

            # 读取meta JSON获取店铺名+货号
            meta_path = os.path.join(self.download_dir, base + "_meta.json")
            shop_info = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as mf:
                    shop_info = json.load(mf)

            shop_name = shop_info.get("shop_name", "").strip()
            goods_no = shop_info.get("goods_no", "").strip()

            # 目录名 = 店铺名称-货号（跟行460-498一致）
            if shop_name and goods_no:
                safe_name = f"{shop_name}-{goods_no}"
            elif shop_name:
                safe_name = shop_name
            elif goods_no:
                safe_name = goods_no
            else:
                safe_name = base
            safe_name = re.sub(r'[\\/:*?"<>|#&]', '', safe_name).strip()
            safe_name = re.sub(r'\s+', '', safe_name)

            extract_path = os.path.join(target_dir, safe_name)
            counter = 1
            while os.path.exists(extract_path):
                extract_path = os.path.join(target_dir, f"{safe_name}_{counter}")
                counter += 1

            if os.path.isdir(extract_path):
                os.remove(zip_path)
                continue

            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_path)

                # 复制店铺信息到解压目录
                import shutil
                if os.path.exists(meta_path):
                    shutil.copy2(meta_path, os.path.join(extract_path, "_店铺信息.json"))
                if shop_info:
                    self._write_shop_marker(extract_path, shop_info)

                os.remove(zip_path)
                if os.path.exists(meta_path):
                    os.remove(meta_path)

                extracted += 1
                print(f"  ✅ {f} → {safe_name}")
            except Exception as e:
                print(f"    ⚠️ 解压失败 {f}: {e}")

        # 清理下载清单
        manifest = os.path.join(self.download_dir, "_下载清单.json")
        if os.path.exists(manifest) and extracted:
            os.remove(manifest)
            print(f"  🗑 已清理: _下载清单.json")

        return extracted

    async def search_keyword(self, keyword, max_results=5):
        """搜索关键词，返回候选商品列表（需已登录）
        优化：跳过¥999占位价、按店铺去重避免同店多件"""
        await self.page.goto("https://cs.17zwd.com/", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)

        search_input = await self.page.query_selector('input.ant-input')
        if not search_input:
            print("  ⚠️ 搜索框未找到")
            return []
        await search_input.fill(keyword)
        await asyncio.sleep(0.5)
        await self.page.keyboard.press("Enter")

        # 等待结果页加载
        try:
            await self.page.wait_for_url("**sks.htm**", timeout=15000)
        except PwTimeout:
            # 如果跳登录页，说明会话过期
            if "login" in self.page.url:
                print("  ⚠️ 会话过期，尝试重新登录...")
                if self.username and self.password:
                    await self.login()
                    # 重新搜索
                    await self.page.goto("https://cs.17zwd.com/", wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    inp = await self.page.query_selector('input.ant-input')
                    if inp:
                        await inp.fill(keyword)
                        await self.page.keyboard.press("Enter")
                        await self.page.wait_for_url("**sks.htm**", timeout=15000)
            else:
                print(f"  ⚠️ 未进入搜索结果页")
                pass

        await asyncio.sleep(5)

        # 滚动加载
        for i in range(5):
            await self.page.evaluate(f"window.scrollTo(0, {i * 500})")
            await asyncio.sleep(0.5)

        await asyncio.sleep(2)

        # 提取商品（含价格过滤+店铺去重）
        items = await self.page.evaluate(f"""() => {{
            const MAX = {max_results};
            let items = []; let seenGid = new Set(); let seenShop = new Set();
            let contents = document.querySelectorAll('[class*="goodsContent"]');
            for (const ct of contents) {{
                if (items.length >= MAX) break;
                let a = ct.querySelector('a[href*="/item/"]');
                if (!a) continue;
                let href = a.getAttribute('href') || '';
                let gid = (href.match(/\\/item\\/(\\d+)/)||[])[1]||'';
                if (!gid || seenGid.has(gid)) continue; seenGid.add(gid);
                let box = ct.querySelector('[class*="goodsInfoBox"]');
                if (!box) continue;
                let price_el = box.querySelector('[class*="goodsPrice"]');
                let price = price_el ? price_el.textContent.trim() : '';
                let priceNum = parseFloat(price.replace(/[¥￥]/g,''));
                // 跳过占位价 ¥999 和异常价格
                if (isNaN(priceNum) || priceNum >= 990) continue;
                if (priceNum < 5 || priceNum > 50) continue;  // 合理批发价范围
                let shop_el = box.querySelector('[class*="shopInfo"]');
                let shop = shop_el ? shop_el.textContent.trim() : '';
                // 跳过童装/儿童类店铺（我们是中老年女装）
                if (shop && (/童装/.test(shop) || /儿童/.test(shop) || /婴儿/.test(shop) || /母婴/.test(shop))) continue;
                // 店铺去重：同一店铺只选一个
                if (shop && seenShop.has(shop)) continue;
                if (shop) seenShop.add(shop);
                let title_el = box.querySelector('[class*="goodsTitle"]');
                let title = title_el ? title_el.textContent.trim() : '(无标题)';
                items.push({{ goods_id: gid, title, price: priceNum.toString(), shop }});
            }}
            return items;
        }}""")
        print(f"  📦 提取结果: {len(items)} 个商品")
        for g in items:
            s = g.get('shop','')[:15]
            print(f"    [{g['goods_id']}] {g.get('title','')[:28]:<30s} ¥{g.get('price','')} | {s}")
        return items if isinstance(items, list) else []


# ===================== CLI 入口 =====================

def build_url(goods_id):
    return f"{BASE_URL}/item/{goods_id}"


async def main_async(args):
    pdd_dir = "/home/pebynn/PDD/商品"
    os.makedirs(pdd_dir, exist_ok=True)
    
    today = time.strftime("%Y-%m-%d")
    if not args.output:
        args.output = os.path.join(pdd_dir, today)
    if not args.extract_to:
        args.extract_to = args.output
    
    print(f"📁 输出目录: {args.output}")
    
    downloader = Downloader17zwd(
        download_dir=args.output,
        headless=not args.debug,
        username=args.username,
        password=args.password,
        debug=args.debug,
    )

    try:
        await downloader.start()

        if args.username and args.password:
            await downloader.login()

        urls = []

        if args.search_keyword:
            print(f"🔍 搜索关键词: {args.search_keyword}")
            goods = await downloader.search_keyword(args.search_keyword, args.max)
            if not goods:
                print("❌ 未搜索到商品")
                return
            print(f"✅ 搜索到 {len(goods)} 个商品:")
            for g in goods:
                print(f"  [{g['goods_id']}] {g.get('title','')[:35]} | ¥{g.get('price','')}")
                urls.append(build_url(g['goods_id']))

        if args.keywords_file:
            with open(args.keywords_file, "r", encoding="utf-8") as f:
                keywords = [l.strip() for l in f if l.strip()]
            for kw in keywords[:args.max_keywords or 5]:
                print(f"🔍 搜索 '{kw}'...")
                goods = await downloader.search_keyword(kw, args.max_per_keyword or 2)
                for g in goods:
                    urls.append(build_url(g['goods_id']))
                await asyncio.sleep(1)

        if args.goods_id:
            urls.append(build_url(args.goods_id))
        if args.url:
            urls.append(args.url)
        if args.url_file:
            with open(args.url_file, "r") as f:
                urls.extend(line.strip() for line in f if line.strip().startswith("http"))
        if args.candidates:
            with open(args.candidates, "r") as f:
                candidates = json.load(f)
            if isinstance(candidates, dict):
                candidates = candidates.get("candidates", candidates.get("items", []))
            for item in candidates:
                if isinstance(item, dict):
                    if "goods_id" in item:
                        urls.append(build_url(item["goods_id"]))
                    elif "link" in item:
                        link = item["link"]
                        if not link.startswith("http"):
                            link = "https://cs.17zwd.com" + link
                        urls.append(link)

        urls = list(dict.fromkeys(urls))[:args.max]
        if not urls:
            print("❌ 请提供 --goods-id、--search-keyword、--keywords-file、--url、--url-file 或 --candidates")
            return

        print(f"📋 待下载: {len(urls)} 个商品")
        for u in urls[:5]:
            print(f"  • {u}")
        if len(urls) > 5:
            print(f"  ... 还有 {len(urls)-5} 个")

        results = await downloader.batch_download(urls)

        manifest = []
        for r in results:
            if r.get("zip") and r.get("shop_info"):
                manifest.append({
                    "zip_file": os.path.basename(r["zip"]),
                    "source_url": r["shop_info"].get("source_url", ""),
                    "shop_name": r["shop_info"].get("shop_name", ""),
                    "shop_address": r["shop_info"].get("shop_address", ""),
                    "goods_no": r["shop_info"].get("goods_no", ""),
                })
        if manifest:
            manifest_path = os.path.join(args.output, "_下载清单.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f"\n📋 下载清单: {manifest_path}")

        if args.extract_to and results:
            downloader.extract_all_zips(args.extract_to)

    finally:
        await downloader.close()


def main():
    parser = argparse.ArgumentParser(
        description="17网供销版商品图片批量下载 v3.0 (Playwright) — 支持搜索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python download_from_17zwd.py --search-keyword 妈妈装 --username 17825029430 --password 17825029430
  python download_from_17zwd.py --keywords-file ./hot_words.json --username 17825029430 --password 17825029430
  python download_from_17zwd.py --goods-id 155155280 --username 17825029430 --password 17825029430

默认输出: /home/pebynn/PDD/商品/yyyy-mm-dd/ (自动按日期分文件夹)
        """
    )
    parser.add_argument("--search-keyword", type=str, help="搜索关键词并下载")
    parser.add_argument("--keywords-file", type=str, help="关键词列表文件")
    parser.add_argument("--max-keywords", type=int, help="最多用几个关键词")
    parser.add_argument("--max-per-keyword", type=int, default=2, help="每关键词最多下载数")
    parser.add_argument("--goods-id", type=str, help="商品ID")
    parser.add_argument("--url", type=str, help="完整商品URL")
    parser.add_argument("--url-file", type=str, help="URL列表文件")
    parser.add_argument("--candidates", type=str, help="候选列表JSON")
    parser.add_argument("--output", "-o", type=str, default="",
                        help="下载目录 (默认 /home/pebynn/PDD/商品/yyyy-mm-dd/)")
    parser.add_argument("--extract-to", type=str, default="",
                        help="解压目录 (默认同 --output)")
    parser.add_argument("--debug", action="store_true",
                        help="调试模式（显示浏览器+截图）")
    parser.add_argument("--max", type=int, default=10, help="最大下载数")
    parser.add_argument("--username", type=str, help="17网账号")
    parser.add_argument("--password", type=str, help="17网密码")

    args = parser.parse_args()

    # 环境变量优先于命令行参数
    env_password = os.environ.get("HERMES_ZW_PASSWORD")
    if env_password:
        args.password = env_password
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
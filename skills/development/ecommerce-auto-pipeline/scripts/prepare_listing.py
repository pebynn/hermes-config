#!/usr/bin/env python3
"""
拼多多商品上架准备工具 v1.0
读取已下载的商品文件夹 → 处理图片 → 生成上架数据

流程：
  1. 读取 _店铺信息.json 获取货源信息
  2. 去水印 → 重命名图片（main_01, detail_01...）
  3. 生成优化标题 + 定价方案
  4. 输出 listing.json（可直接对接PDD API）

用法：
    # 处理一个商品
    python prepare_listing.py --input /home/pebynn/PDD/商品/2026-04-27/卡彤网批-001

    # 批量处理当天所有商品
    python prepare_listing.py --date 2026-04-27

    # 只预览不上架
    python prepare_listing.py --date 2026-04-27 --preview
"""

import os
import sys
import json
import re
import argparse
import time
from pathlib import Path

# DeepSeek API 标题优化 — 从 ~/.hermes/.env 读取
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def _load_deepseek_key():
    """从 .env 文件读取 DeepSeek API Key"""
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image
except ImportError:
    print("❌ 需要 Pillow: pip install Pillow")
    sys.exit(1)

OUTPUT_ROOT = os.path.expanduser("~/PDD/商品")

# ===================== 定价模型 =====================

def _classify_tier(cost_price, style_type=None):
    """根据拿货价 + 款式特征自动分档。

    纯成本阈值（不含物流杂费）：
        < 30 → traffic  （引流款）
        30~60 → profit  （利润款）
        > 60  → image   （形象款）

    style_type 辅助提示（优先级低于显式 tier，高于纯 cost 判断）：
        "basic"   → 倾向 traffic（基础款如 T 恤、打底衫）
        "set"     → 倾向 profit  （搭配款如套装、连衣裙）
        "premium" → 倾向 image   （特殊面料/设计款）
    """
    CATEGORIES = {
        "traffic": {"low": 0, "high": 30},
        "profit":  {"low": 30, "high": 60},
        "image":   {"low": 60, "high": float("inf")},
    }

    def _find_category(price):
        for cat, rng in CATEGORIES.items():
            if rng["low"] <= price < rng["high"]:
                return cat
        return "profit"

    cat = _find_category(cost_price)

    # style_type 做软降级/升级调整（仅当处于边界区间时生效）
    style_shifts = {"basic": "traffic", "set": "profit", "premium": "image"}
    preferred = style_shifts.get(style_type)
    if preferred and preferred != cat:
        cat = preferred

    return cat


def calc_price(cost_price, tier=None, style_type=None):
    """
    定价公式（来自 skill 定价策略）

    cost_price : 17网拿货价（商品本身价格，不含运费包装保险）
    tier       : 手动指定 tier ("traffic"/"profit"/"image"), 默认 None → 自动判断
    style_type : 可选款式提示 ("basic"/"set"/"premium"), 影响自动分档

    返回 (建议售价, 定价明细 dict)
    """
    shipping = 4
    packaging = 1
    insurance = 0.5
    hard_cost = cost_price + shipping + packaging + insurance

    # ── 确定最终使用的 tier ──────────────────────────────
    if tier is None:
        tier = _classify_tier(cost_price, style_type)

    params = {
        "traffic": {"markup": 1.3, "return_rate": 0.20, "ad_rate": 0.10},
        "profit":  {"markup": 1.5, "return_rate": 0.20, "ad_rate": 0.10},
        "image":   {"markup": 1.8, "return_rate": 0.20, "ad_rate": 0.10},
    }
    p = params[tier]
    commission = 0.006
    price = hard_cost * p["markup"] / (1 - p["return_rate"] - p["ad_rate"] - commission)
    price = round(price / 10) * 10 - 0.1
    price = max(price, 29.9)

    profit = price - hard_cost - price * commission - price * p["ad_rate"]
    profit -= profit * p["return_rate"]  # 退货扣除利润部分

    detail = {
        "tier": tier,
        "cost_price": cost_price,
        "hard_cost": round(hard_cost, 2),
        "markup": p["markup"],
        "return_rate": p["return_rate"],
        "ad_rate": p["ad_rate"],
        "commission": commission,
        "suggested_price": round(price, 2),
        "estimated_profit": round(profit, 2),
        "estimated_profit_before_return": round(price - hard_cost - price * (commission + p["ad_rate"]), 2),
        "auto_tier": tier == _classify_tier(cost_price, style_type),  # True = 自动判定, False = 手动指定
    }
    return round(price, 2), detail


# ===================== AI标题优化 =====================

def optimize_title_with_ai(original_title, price, sku_info):
    """调用 DeepSeek 生成拼多多优化标题（限60字）"""
    if not HAS_REQUESTS or not original_title or len(original_title) < 5:
        return None

    colors = sku_info.get("colors", [])
    sizes = sku_info.get("sizes", [])

    prompt = f"""你是一个拼多多商品标题优化专家。根据以下信息生成一个**不超过60字**的拼多多商品标题。

原商品标题: {original_title}
价格: ¥{price}
颜色选项: {', '.join(colors) if colors else '无'}
尺码选项: {', '.join(sizes) if sizes else '均码'}

规则：
1. 限制60字以内（非常重要！）
2. 包含核心品类词（如 女装、套装、连衣裙、T恤）
3. 包含目标人群词（中老年、妈妈装）
4. 包含属性词（显瘦、冰丝、宽松、2026新款）
5. 自然通顺，不要关键词堆砌
6. 不要出现店铺名、货号、联系方式

直接输出标题，不要任何解释。"""

    try:
        api_key = _load_deepseek_key()
        if not api_key:
            return None
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个拼多多商品标题优化专家，生成简洁有效的商品标题。"},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 100,
                "temperature": 0.3,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            result = resp.json()["choices"][0]["message"]["content"].strip()
            # 清理可能的引号和多余字符
            result = result.strip('"\'""').strip()
            if result and len(result) <= 60:
                return result
        return None
    except Exception as e:
        print(f"    ⚠️ AI标题优化失败: {e}")
        return None


# ===================== 标题优化（关键词匹配，AI降级后备）=====================

TITLE_TEMPLATES = {
    "中老年": "中老年{品类}{特征}{材质}{版型}{风格}",
    "套装":   "{风格}{品类}{特征}{材质}套装",
}

CATEGORY_KEYWORDS = [
    "中老年", "妈妈装", "奶奶装", "大码",
    "套装", "两件套", "三件套", "运动套装",
    "连衣裙", "T恤", "衬衫", "阔腿裤", "旗袍",
    "新中式", "国风", "民族风", "唐装",
]

FEATURE_KEYWORDS = [
    "显瘦", "遮肚腩", "宽松", "修身", "冰丝",
    "纯棉", "真丝", "雪纺", "透气", "防晒",
    "2026新款", "夏季", "春秋", "冬装",
    "洋气", "时尚", "气质", "高档",
    "休闲", "运动", "舒适",
]

MATERIAL_KEYWORDS = [
    "冰丝", "纯棉", "真丝", "雪纺", "棉麻",
    "聚酯纤维", "氨纶", "蕾丝", "牛仔",
]

STYLE_KEYWORDS = [
    "新中式", "国风", "简约", "韩版", "民族风",
    "复古", "法式", "通勤", "休闲",
]

def generate_title(shop_info, original_title, price=0, sku_info=None):
    """从原标题和店铺信息生成优化标题（PDD限60字）
    优先调用AI优化，失败回退关键词匹配
    """
    # 先试 AI 优化
    if price > 0 and original_title and len(original_title) >= 5:
        ai_title = optimize_title_with_ai(original_title, price, sku_info or {})
        if ai_title:
            return ai_title

    # 降级：关键词匹配
    # 提取关键信息
    title_lower = original_title.lower()
    words = original_title

    # 提取特征词
    features = [w for w in FEATURE_KEYWORDS if w in words]
    materials = [w for w in MATERIAL_KEYWORDS if w in words]
    styles = [w for w in STYLE_KEYWORDS if w in words]
    categories = [w for w in CATEGORY_KEYWORDS if w in words]

    # 确定品类方向
    is_mid_old = any(k in words for k in ["中老年", "妈妈", "奶奶"])
    is_set = any(k in words for k in ["套装", "两件套", "三件套"])

    # 构建新标题
    title_parts = []

    # 目标人群
    if is_mid_old:
        title_parts.append("中老年")
    if "大码" in words:
        title_parts.append("大码")

    # 年份+季节
    if "2026" in words or "新款" in words:
        if "夏季" in words or "夏" in words:
            title_parts.append("2026夏季新款")
        elif "春秋" in words:
            title_parts.append("2026春秋新款")
        else:
            title_parts.append("2026新款")

    # 特征
    if features:
        title_parts.append(features[0])

    # 风格
    if styles:
        title_parts.append(styles[0])

    # 品类（核心）
    core_cat = ""
    if is_set:
        core_cat = "套装"
    elif "连衣裙" in words or "旗袍" in words or "裙子" in words:
        core_cat = "连衣裙" if "连衣裙" in words else ("旗袍" if "旗袍" in words else "裙子")
    elif "T恤" in words or "t恤" in words:
        core_cat = "T恤"
    elif "衬衫" in words or "衫" in words:
        core_cat = "衬衫"
    elif "裤" in words:
        core_cat = "阔腿裤" if "阔腿" in words else "裤子"
    elif "外套" in words or "大衣" in words:
        core_cat = "外套"
    elif "上衣" in words:
        core_cat = "上衣"
    else:
        # 从原标题取最后有意义的名词
        for c in reversed(CATEGORY_KEYWORDS):
            if c in words:
                core_cat = c
                break
        if not core_cat:
            core_cat = "女装"

    title_parts.append(core_cat)

    # 材质
    if materials:
        title_parts.append(materials[0])

    # 货号（作为唯一标识）
    goods_no = shop_info.get("goods_no", "").strip("# ")

    title = " ".join(title_parts)

    # 限60字
    if len(title) > 55:
        title = title[:55]

    return title


# ===================== 图片处理 =====================

def process_images(product_dir, shop_info, preview=False):
    """处理商品图片：去水印+重命名
    返回 {main_images: [...], detail_images: [...], processed_count: N}
    """
    listing_dir = os.path.join(product_dir, "listing-ready")
    if not preview:
        os.makedirs(listing_dir, exist_ok=True)

    result = {"main_images": [], "detail_images": [], "processed_count": 0}

    for sub_dir in ["主图", "详情图", "属性图"]:
        src_path = os.path.join(product_dir, sub_dir)
        if not os.path.isdir(src_path):
            continue

        images = sorted([
            f for f in os.listdir(src_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])

        for idx, fname in enumerate(images):
            src_file = os.path.join(src_path, fname)

            # 归类：主图前缀main_，其他detail_
            prefix = "main" if sub_dir == "主图" else "detail"
            new_name = f"{prefix}_{idx + 1:02d}.jpg"
            dest_file = os.path.join(listing_dir, new_name)

            if preview:
                result["main_images" if sub_dir == "主图" else "detail_images"].append({
                    "original": fname,
                    "renamed": new_name,
                    "source": sub_dir,
                    "file": "",
                })
                continue

            try:
                img = Image.open(src_file)
                # 转RGB保存为JPG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # 去水印（右下角区域用邻域像素覆盖）
                if hasattr(img, 'size') and img.size[0] > 100 and img.size[1] > 100:
                    w, h = img.size
                    # 右下角水印区域（约100x30像素区域）
                    watermark_roi = (max(0, w - 120), max(0, h - 40), w, h)
                    # 用上方相邻区域填充
                    fill_area = (watermark_roi[0], max(0, watermark_roi[1] - 40),
                                 watermark_roi[2], watermark_roi[3] - 40)
                    fill_region = img.crop(fill_area)
                    img.paste(fill_region, watermark_roi)

                img.save(dest_file, "JPEG", quality=92)

                key = "main_images" if sub_dir == "主图" else "detail_images"
                result[key].append({
                    "original": fname,
                    "renamed": new_name,
                    "source": sub_dir,
                    "file": dest_file,
                })
                result["processed_count"] += 1
            except Exception as e:
                print(f"    ⚠️ 处理失败 {fname}: {e}")

    return result


# ===================== 生成上架数据 =====================

def generate_listing(product_dir, shop_info, image_result, original_title, tier=None):
    """生成完整的上架数据JSON

    tier : 手动指定 tier 覆盖自动分档；默认 None → 自动判断
    """
    cost_price = float(shop_info.get("price", 0))
    if cost_price <= 0:
        cost_price = 25

    # 尝试从店铺信息读取款式提示（可选）
    style_type = shop_info.get("style_type")  # 如果 JSON 中定义了
    price, price_detail = calc_price(cost_price, tier=tier, style_type=style_type)

    # 品类定价上限：中老年女装 max_price=299
    MAX_PRICE = 299
    if price > MAX_PRICE:
        price = MAX_PRICE
        # 重新生成定价明细以反映上限限制
        price_detail = price_detail.copy()
        price_detail["suggested_price"] = float(MAX_PRICE)
        # 按上限重新计算预计净利
        hard_cost = price_detail["hard_cost"]
        commission = price_detail.get("commission", 0.006)
        ad_rate = price_detail.get("ad_rate", 0.10)
        return_rate = price_detail.get("return_rate", 0.25)
        profit_ceiling = MAX_PRICE - hard_cost - MAX_PRICE * (commission + ad_rate)
        profit_ceiling -= profit_ceiling * return_rate
        price_detail["estimated_profit"] = round(profit_ceiling, 2)
        price_detail["price_capped"] = True
        price_detail["max_price"] = MAX_PRICE

    # 生成SKU：颜色×尺码 笛卡尔积
    sku_info = shop_info.get("sku", {})
    colors = sku_info.get("colors", [])
    sizes = sku_info.get("sizes", [])
    # 均码/单码 → 自动扩展为 L/XL/2XL/3XL/4XL/5XL 六码
    if len(sizes) <= 1:
        sizes = ["L", "XL", "2XL", "3XL", "4XL", "5XL"]
    sku_list = []
    if colors and sizes:
        for c in colors:
            for s in sizes:
                sku_list.append({
                    "spec": f"{c},{s}",
                    "price": int(price * 100),
                    "quantity": 1000,
                })
    elif colors:
        for c in colors:
            sku_list.append({
                "spec": c,
                "price": int(price * 100),
                "quantity": 1000,
            })
    elif sizes:
        for s in sizes:
            sku_list.append({
                "spec": s,
                "price": int(price * 100),
                "quantity": 1000,
            })
    else:
        sku_list.append({
            "spec": "均码",
            "price": int(price * 100),
            "quantity": 1000,
        })

    listing = {
        "goods_name": generate_title(shop_info, original_title, price, shop_info.get("sku", {})),
        "cat_id": None,
        "market_price": int(price * 1.5 * 100),
        "goods_price": int(price * 100),
        "goods_number": sum(s["quantity"] for s in sku_list),
        "main_images": [img["file"] for img in image_result.get("main_images", [])],
        "detail_images": [img["file"] for img in image_result.get("detail_images", [])],
        "sku_list": sku_list,
        # 后台管理
        "out_goods_id": shop_info.get("goods_no", ""),
        "remark": f"来源: {shop_info.get('shop_name', '')}/{shop_info.get('shop_address', '')[:30]}/货号{shop_info.get('goods_no', '')}",
        # 定价明细
        "pricing": price_detail,
        # 货源
        "source": {
            "shop_name": shop_info.get("shop_name", ""),
            "shop_address": shop_info.get("shop_address", ""),
            "goods_no": shop_info.get("goods_no", ""),
        },
    }

    return listing


# ===================== 主流程 =====================

def process_product(product_dir, preview=False, tier=None):
    """处理单个商品

    tier : 手动指定 tier 覆盖自动分档；默认 None → 根据拿货价自动判断
    """
    dir_name = os.path.basename(product_dir)
    print(f"\n{'─'*50}")
    print(f"  📦 {dir_name}")
    print(f"{'─'*50}")

    # 读取店铺信息
    meta_path = os.path.join(product_dir, "_店铺信息.json")
    if not os.path.exists(meta_path):
        print(f"  ⚠️ 无 _店铺信息.json，跳过")
        return None

    with open(meta_path, "r", encoding="utf-8") as f:
        shop_info = json.load(f)

    # 价格：优先从 _店铺信息.json 取，兜底从货源信息.txt 正则
    cost_price = shop_info.get("price", 0)
    if not cost_price:
        source_txt = os.path.join(product_dir, "货源信息.txt")
        if os.path.exists(source_txt):
            with open(source_txt, "r") as f:
                content = f.read()
                m = re.search(r'拿货价.*?¥?(\d+[\.]?\d*)', content)
                if m:
                    cost_price = float(m.group(1))

    shop_name = shop_info.get("shop_name", "?")
    goods_no = shop_info.get("goods_no", "?")
    display_price = f"¥{cost_price}" if cost_price else "?"
    print(f"  店铺: {shop_name}  货号: {goods_no}  拿货价: {display_price}")

    # 处理图片
    print(f"  🖼 处理图片...")
    img_result = process_images(product_dir, shop_info, preview)

    if preview:
        print(f"    主图: {len(img_result['main_images'])}张")
        print(f"    详情图: {len(img_result['detail_images'])}张")
    else:
        print(f"    ✅ {img_result['processed_count']} 张已处理 → listing-ready/")

    # 生成上架数据
    original_title = shop_info.get("title", "") or dir_name
    listing = generate_listing(product_dir, shop_info, img_result, original_title, tier)

    # 输出
    print(f"\n  📋 上架预览:")
    print(f"    标题: {listing['goods_name'][:50]}...")
    print(f"    售价: ¥{listing['goods_price']/100:.1f} (拿货{display_price})")
    print(f"    主图: {len(listing['main_images'])}张")
    print(f"    详情: {len(listing['detail_images'])}张")
    print(f"    备注: {listing['remark'][:50]}...")

    if not preview:
        output_path = os.path.join(product_dir, "listing-ready", "listing.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(listing, f, ensure_ascii=False, indent=2)

        # 写定价明细
        price_path = os.path.join(product_dir, "listing-ready", "定价方案.txt")
        pd_detail = listing["pricing"]
        pd_content = f"""========================================
  上架定价方案
========================================
  拿货价:    ¥{pd_detail['cost_price']}
  硬成本:    ¥{pd_detail['hard_cost']}
  倍率:      {pd_detail['markup']}x
  建议售价:  ¥{pd_detail['suggested_price']}
  预计净利:  ¥{pd_detail['estimated_profit']}/件
  退货率:    {pd_detail['return_rate']*100}%
  推广费率:  {pd_detail['ad_rate']*100}%
========================================
"""
        with open(price_path, "w", encoding="utf-8") as f:
            f.write(pd_content)
        print(f"    ✅ 已保存: listing.json + 定价方案.txt")

    return listing


def main():
    parser = argparse.ArgumentParser(
        description="拼多多上架准备工具 — 图片处理+定价+数据生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", type=str, help="商品目录路径")
    group.add_argument("--date", "-d", type=str, help="日期文件夹，如 2026-04-27")
    parser.add_argument("--preview", action="store_true", help="只预览，不处理图片")
    parser.add_argument("--tier", type=str, default=None,
                        choices=["traffic", "profit", "image"],
                        help="定价策略: traffic(引流)/profit(利润)/image(形象). 不传时根据拿货价自动判断")

    args = parser.parse_args()

    if args.date:
        base_dir = os.path.join(OUTPUT_ROOT, args.date)
        if not os.path.isdir(base_dir):
            print(f"❌ 目录不存在: {base_dir}")
            sys.exit(1)
        products = sorted([
            os.path.join(base_dir, d) for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
        ])
    else:
        products = [args.input]

    print(f"{'='*50}")
    print(f"  📤 拼多多上架准备")
    print(f"  模式: {'预览' if args.preview else '正式处理'}")
    print(f"  定价: {args.tier if args.tier else 'auto'}")
    print(f"  商品: {len(products)} 个")
    print(f"{'='*50}")

    all_listings = []
    for product_dir in products:
        listing = process_product(product_dir, args.preview, args.tier)
        if listing:
            all_listings.append(listing)

    print(f"\n{'='*50}")
    print(f"  ✅ 完成: {len(all_listings)}/{len(products)} 个商品准备就绪")
    if not args.preview:
        print(f"  图片在: listing-ready/ 目录下")
        print(f"  定价方案: 定价方案.txt")
        print(f"  上架数据: listing.json (可对接PDD API)")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
3_review_manager.py — 评价管理

支持：
- 模拟评价生成
- 评价列表/差评识别
- 差评回复模板
- 好评引导

用法：
    # 生成模拟评价
    python 3_review_manager.py --generate --count 5

    # 列出所有评价
    python 3_review_manager.py --list

    # 只列差评（<4星）
    python 3_review_manager.py --list --negative-only

    # 回复评价
    python 3_review_manager.py --reply RV202604280001 --content "感谢您的反馈，我们会持续改进"

数据目录: ~/PDD/运营/reviews/YYYY-MM-DD.json
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime

OPS_ROOT = os.path.expanduser("~/PDD/运营")
REVIEWS_DIR = os.path.join(OPS_ROOT, "reviews")


REPLY_TEMPLATES = {
    "positive": [
        "感谢您的认可和支持！我们会继续努力提供优质商品和服务 🌹",
        "谢谢亲的好评！欢迎再次光临~",
        "您的满意是我们最大的动力！祝您生活愉快 ❤️",
    ],
    "negative": [
        "亲，非常抱歉给您带来不好的体验。我们会认真反思和改进，如有问题请联系客服处理。",
        "感谢您的反馈，我们已记录并会优化产品质量。如果您需要退换货，请联系在线客服。",
        "抱歉让您失望了。我们会加强品质管控，期待您给我们改进的机会 🙏",
    ],
}


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def ensure_dirs():
    os.makedirs(REVIEWS_DIR, exist_ok=True)


def get_reviews_file(date_str: str = None) -> str:
    date_str = date_str or time.strftime("%Y-%m-%d")
    return os.path.join(REVIEWS_DIR, f"{date_str}.json")


def load_reviews(date_str: str = None) -> list:
    fpath = get_reviews_file(date_str)
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_reviews(reviews: list, date_str: str = None):
    fpath = get_reviews_file(date_str)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


NEGATIVE_COMMENTS = [
    "质量一般，面料有点硬",
    "和图片颜色不太一样，偏深",
    "尺码偏大，换成小一号就好了",
    "做工有点粗糙有线头",
    "穿了几天就起球了",
    "快递太慢了",
    "和描述不太相符",
    "不值这个价格",
]

POSITIVE_COMMENTS = [
    "质量很好，面料舒服",
    "颜色和图片一样好看",
    "穿上很合身，显气质",
    "妈妈很喜欢，好评",
    "性价比很高，推荐",
    "做工精细，没有线头",
    "发货很快，满意",
    "版型很好，显瘦",
]


def generate_mock_review(index: int) -> dict:
    """生成模拟评价"""
    goods = [
        "中老年妈妈夏装宽松显瘦连衣裙",
        "中老年冰丝套装两件套",
        "妈妈装雪纺衫短袖上衣",
        "中老年阔腿裤高腰",
    ]
    today = datetime.now().strftime("%Y%m%d")
    is_negative = random.random() < 0.3  # 30%差评率
    rating = random.randint(1, 2) if is_negative else random.randint(4, 5)
    comment = random.choice(NEGATIVE_COMMENTS if is_negative else POSITIVE_COMMENTS)

    return {
        "review_id": f"RV{today}{index:04d}",
        "order_id": f"PDD{today}{random.randint(1,100):04d}",
        "goods_name": random.choice(goods),
        "rating": rating,
        "content": comment,
        "is_negative": is_negative,
        "reply": None,
        "time": datetime.now().isoformat(),
    }


def cmd_generate(count: int, date_str: str):
    reviews = load_reviews(date_str)
    existing_ids = {r["review_id"] for r in reviews}
    new_count = 0
    for i in range(count):
        r = generate_mock_review(len(reviews) + i + 1)
        if r["review_id"] not in existing_ids:
            reviews.append(r)
            existing_ids.add(r["review_id"])
            new_count += 1
    save_reviews(reviews, date_str)
    log(f"生成 {new_count} 条评价（共 {len(reviews)} 条）", "OK")


def cmd_list(date_str: str, negative_only: bool = False, unreplied: bool = False):
    reviews = load_reviews(date_str)
    if not reviews:
        log(f"{date_str} 无评价数据", "INFO")
        return

    if negative_only:
        reviews = [r for r in reviews if r.get("is_negative")]
    if unreplied:
        reviews = [r for r in reviews if r.get("reply") is None]

    print(f"\n  {'='*55}")
    print(f"  评价列表 ({date_str}) 共 {len(reviews)} 条")
    if negative_only:
        print(f"  筛选: 差评")
    if unreplied:
        print(f"  筛选: 未回复")
    print(f"  {'='*55}")

    negative_count = 0
    for r in reviews:
        stars = "⭐" * r.get("rating", 5)
        replied = "💬" if r.get("reply") else "🔇"
        neg = "⚠️" if r.get("is_negative") else "  "
        print(f"  {neg} {r['review_id']}  {r['goods_name'][:20]:20s} "
              f"{stars} {replied} [{r.get('content','')[:15]}]")
        if r.get("is_negative"):
            negative_count += 1
        if r.get("reply"):
            print(f"       ↪ {r['reply'][:40]}")

    avg_rating = sum(r.get("rating", 5) for r in reviews) / len(reviews) if reviews else 0
    print(f"  {'─'*55}")
    print(f"  平均评分: {avg_rating:.1f}⭐  差评率: {negative_count/len(reviews)*100:.0f}%  ({negative_count}/{len(reviews)})")
    print(f"  {'='*55}")


def cmd_reply(review_id: str, content: str, date_str: str = None):
    """回复评价"""
    if date_str:
        reviews = load_reviews(date_str)
        for r in reviews:
            if r["review_id"] == review_id:
                r["reply"] = content
                save_reviews(reviews, date_str)
                log(f"评价 {review_id} 已回复", "OK")
                return
    else:
        for fname in sorted(os.listdir(REVIEWS_DIR)):
            if fname.endswith(".json"):
                ds = fname.replace(".json", "")
                reviews = load_reviews(ds)
                for r in reviews:
                    if r["review_id"] == review_id:
                        r["reply"] = content
                        save_reviews(reviews, ds)
                        log(f"评价 {review_id} 已回复 (in {ds})", "OK")
                        return
    log(f"未找到评价: {review_id}", "WARN")


def cmd_batch_reply_negative(date_str: str):
    """批量回复所有未回复差评"""
    reviews = load_reviews(date_str)
    count = 0
    for r in reviews:
        if r.get("is_negative") and r.get("reply") is None:
            r["reply"] = random.choice(REPLY_TEMPLATES["negative"])
            count += 1
    if count > 0:
        save_reviews(reviews, date_str)
        log(f"已回复 {count} 条差评", "OK")
    else:
        log("没有未回复的差评", "INFO")


def main():
    parser = argparse.ArgumentParser(
        description="评价管理 — 列表/差评识别/回复/批量处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", "-d", type=str, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--generate", action="store_true", help="生成模拟评价")
    parser.add_argument("--count", type=int, default=5, help="生成数量")
    parser.add_argument("--list", action="store_true", help="列出评价")
    parser.add_argument("--negative-only", action="store_true", help="只列差评")
    parser.add_argument("--unreplied", action="store_true", help="只列未回复")
    parser.add_argument("--reply", type=str, help="回复评价 (review_id)")
    parser.add_argument("--content", type=str, default="", help="回复内容")
    parser.add_argument("--batch-reply-negative", action="store_true", help="批量回复差评")

    args = parser.parse_args()
    today = time.strftime("%Y-%m-%d")
    date_str = args.date or today

    ensure_dirs()

    if args.generate:
        cmd_generate(args.count, date_str)
    elif args.list:
        cmd_list(date_str, args.negative_only, args.unreplied)
    elif args.reply:
        if not args.content:
            log("请指定 --content", "ERR")
            sys.exit(1)
        cmd_reply(args.reply, args.content, date_str)
    elif args.batch_reply_negative:
        cmd_batch_reply_negative(date_str)
    else:
        cmd_list(date_str)


if __name__ == "__main__":
    main()

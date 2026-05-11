#!/usr/bin/env python3
"""
2_return_refund.py — 退货退款处理

支持：
- 模拟退货申请生成
- 退货列表/详情/审核
- 同意/拒绝/退款操作

用法：
    # 生成模拟退货申请
    python 2_return_refund.py --generate --count 3

    # 列出待处理退货
    python 2_return_refund.py --list --status pending

    # 查看退货详情
    python 2_return_refund.py --view R202604280001

    # 审核退货
    python 2_return_refund.py --approve R202604280001
    python 2_return_refund.py --reject R202604280001 --reason "不影响二次销售"
    python 2_return_refund.py --refund R202604280001

数据目录: ~/PDD/运营/returns/YYYY-MM-DD.json
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime

OPS_ROOT = os.path.expanduser("~/PDD/运营")
RETURNS_DIR = os.path.join(OPS_ROOT, "returns")


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "STEP": "📌"}.get(level, "•")
    print(f"  {icon} [{ts}] {msg}")


def ensure_dirs():
    os.makedirs(RETURNS_DIR, exist_ok=True)


def get_returns_file(date_str: str = None) -> str:
    date_str = date_str or time.strftime("%Y-%m-%d")
    return os.path.join(RETURNS_DIR, f"{date_str}.json")


def load_returns(date_str: str = None) -> list:
    fpath = get_returns_file(date_str)
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_returns(returns: list, date_str: str = None):
    fpath = get_returns_file(date_str)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(returns, f, ensure_ascii=False, indent=2)


def generate_mock_return(index: int) -> dict:
    """生成模拟退货申请"""
    reasons = [
        "尺码不合适",
        "颜色与图片不符",
        "质量有问题（线头/脱线）",
        "面料不喜欢",
        "发错货",
        "穿着不好看",
    ]
    goods = [
        ("中老年妈妈夏装宽松显瘦连衣裙", "黑色,XL", 7990),
        ("中老年冰丝套装两件套", "深蓝,2XL", 8990),
        ("妈妈装雪纺衫短袖上衣", "碎花,L", 5990),
    ]
    goods_name, sku_spec, price = random.choice(goods)
    today = datetime.now().strftime("%Y%m%d")

    return {
        "return_id": f"R{today}{index:04d}",
        "order_id": f"PDD{today}{random.randint(1,100):04d}",
        "goods_name": goods_name,
        "sku_spec": sku_spec,
        "reason": random.choice(reasons),
        "status": "pending",
        "apply_time": datetime.now().isoformat(),
        "amount": price,
        "approved_time": None,
        "reject_reason": None,
    }


def cmd_generate(count: int, date_str: str):
    returns = load_returns(date_str)
    existing_ids = {r["return_id"] for r in returns}
    new_count = 0
    for i in range(count):
        r = generate_mock_return(len(returns) + i + 1)
        if r["return_id"] not in existing_ids:
            returns.append(r)
            existing_ids.add(r["return_id"])
            new_count += 1
    save_returns(returns, date_str)
    log(f"生成 {new_count} 条退货申请（共 {len(returns)} 条）", "OK")


def cmd_list(date_str: str, status: str = None):
    returns = load_returns(date_str)
    if not returns:
        log(f"{date_str} 无退货数据", "INFO")
        return
    if status:
        returns = [r for r in returns if r.get("status") == status]

    print(f"\n  {'='*55}")
    print(f"  退货列表 ({date_str}) 共 {len(returns)} 条")
    if status:
        print(f"  筛选: status={status}")
    print(f"  {'='*55}")

    for r in returns:
        amount_yuan = r["amount"] / 100
        status_icon = {"pending": "⏳", "approved": "✅",
                       "rejected": "❌", "refunded": "💰"}.get(r.get("status", ""), "•")
        print(f"  {status_icon} {r['return_id']}  {r['goods_name'][:20]:20s} "
              f"¥{amount_yuan:.1f}  {r['status']}  [{r.get('reason','')[:10]}]")

    print(f"  {'='*55}")


def _find_return(return_id: str, date_str: str = None):
    """查找退货单。返回 (returns列表, index, date_str) 或 None"""
    if date_str:
        returns = load_returns(date_str)
        for i, r in enumerate(returns):
            if r["return_id"] == return_id:
                return returns, i, date_str
    else:
        for fname in sorted(os.listdir(RETURNS_DIR)):
            if fname.endswith(".json"):
                ds = fname.replace(".json", "")
                returns = load_returns(ds)
                for i, r in enumerate(returns):
                    if r["return_id"] == return_id:
                        return returns, i, ds
    return None


def cmd_view(return_id: str, date_str: str = None):
    result = _find_return(return_id, date_str)
    if not result:
        log(f"未找到退货单: {return_id}", "WARN")
        return
    returns, idx, ds = result
    r = returns[idx]

    print(f"\n  {'='*55}")
    print(f"  退货详情: {return_id}")
    print(f"  {'='*55}")
    for k, v in r.items():
        if k == "amount" and isinstance(v, (int, float)):
            print(f"    {k}: ¥{v/100:.2f}")
        else:
            print(f"    {k}: {v}")
    print(f"  {'='*55}")


def cmd_approve(return_id: str, date_str: str = None):
    result = _find_return(return_id, date_str)
    if not result:
        log(f"未找到退货单: {return_id}", "WARN")
        return
    returns, idx, ds = result
    r = returns[idx]
    if r["status"] != "pending":
        log(f"退货单 {return_id} 当前状态 {r['status']}，无法批准", "WARN")
        return
    r["status"] = "approved"
    r["approved_time"] = datetime.now().isoformat()
    save_returns(returns, ds)
    log(f"退货单 {return_id} 已批准", "OK")


def cmd_reject(return_id: str, reason: str, date_str: str = None):
    result = _find_return(return_id, date_str)
    if not result:
        log(f"未找到退货单: {return_id}", "WARN")
        return
    returns, idx, ds = result
    r = returns[idx]
    if r["status"] != "pending":
        log(f"退货单 {return_id} 当前状态 {r['status']}，无法拒绝", "WARN")
        return
    r["status"] = "rejected"
    r["reject_reason"] = reason
    save_returns(returns, ds)
    log(f"退货单 {return_id} 已拒绝: {reason}", "OK")


def cmd_refund(return_id: str, date_str: str = None):
    result = _find_return(return_id, date_str)
    if not result:
        log(f"未找到退货单: {return_id}", "WARN")
        return
    returns, idx, ds = result
    r = returns[idx]
    if r["status"] != "approved":
        log(f"退货单 {return_id} 当前状态 {r['status']}，需先批准才能退款", "WARN")
        return
    r["status"] = "refunded"
    save_returns(returns, ds)
    amount_yuan = r["amount"] / 100
    log(f"退货单 {return_id} 已退款 ¥{amount_yuan:.2f}", "OK")


def main():
    parser = argparse.ArgumentParser(
        description="退货退款处理 — 申请/审核/退款全流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", "-d", type=str, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--generate", action="store_true", help="生成模拟退货")
    parser.add_argument("--count", type=int, default=3, help="生成数量")
    parser.add_argument("--list", action="store_true", help="列出退货")
    parser.add_argument("--view", type=str, help="查看退货详情")
    parser.add_argument("--approve", type=str, help="批准退货 (return_id)")
    parser.add_argument("--reject", type=str, help="拒绝退货 (return_id)")
    parser.add_argument("--reason", type=str, default="不符合退货条件", help="拒绝原因")
    parser.add_argument("--refund", type=str, help="执行退款 (return_id)")
    parser.add_argument("--filter-status", type=str, help="筛选状态: pending/approved/rejected/refunded")

    args = parser.parse_args()
    today = time.strftime("%Y-%m-%d")
    date_str = args.date or today

    ensure_dirs()

    if args.generate:
        cmd_generate(args.count, date_str)
    elif args.list:
        cmd_list(date_str, args.filter_status)
    elif args.view:
        cmd_view(args.view, date_str)
    elif args.approve:
        cmd_approve(args.approve, date_str)
    elif args.reject:
        cmd_reject(args.reject, args.reason, date_str)
    elif args.refund:
        cmd_refund(args.refund, date_str)
    else:
        cmd_list(date_str)


if __name__ == "__main__":
    main()

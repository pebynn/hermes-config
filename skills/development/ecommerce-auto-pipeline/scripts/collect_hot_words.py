#!/usr/bin/env python3
"""
电商热搜词采集工具 v2.0 — 三大平台交叉验证版
采集方式（全部 requests，无需浏览器）：
  - 淘宝 suggest API（10词/种子，支持递归展开）
  - 拼多多首页热搜（20个热搜词，HTML嵌入式JSON）
  - 抖音热搜榜 API（50个热搜词）
输出：JSON 格式，带平台来源标记，交叉验证（词出现在2+平台 = 高置信）

用法：
    python collect_hot_words.py
    python collect_hot_words.py --seeds "连衣裙,卫衣" --top 30
    python collect_hot_words.py --cross-only        # 只显示跨平台词
    python collect_hot_words.py --recursive         # 递归展开（suggest结果作新种子）
    python collect_hot_words.py --platforms taobao,douyin
    python collect_hot_words.py --output ./hot_words.json
"""

import requests
import json
import time
import re
import argparse
import sys
from collections import defaultdict
from urllib.parse import quote

# ===================== 常量 =====================

FASHION_FILTER = re.compile(r'[装裙裤衫服鞋帽包饰袜带衣领袖扣襟褶摆]')
NON_FASHION = re.compile(
    r'(科技|体育|政治|游戏|娱乐|明星|电视剧|电影|综艺|财经|'
    r'军事|汽车|数码|手机|电脑|房产|教育|医疗|健康|'
    r'高考|考研|公务员|考试|天气|交通|旅游|景点|'
    r'社会|新闻|热点|事件|曝光|热搜|蓝牙|耳机|蚊香|'
    r'蚊帐|猫粮|猫砂|牙膏|洗面奶|洗脸巾|沐浴露|洗衣液|'
    r'拖鞋|内裤)'
)
REQ_TIMEOUT = 8
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
MOBILE_UA = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36"
}

# ===================== 平台采集器 =====================


def fetch_taobao_suggest(keyword, retries=2):
    """淘宝 suggest API — ✅ 每个种子返回10个推荐词"""
    url = "https://suggest.taobao.com/sug"
    params = {"code": "utf-8", "q": keyword, "callback": ""}
    for _ in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=REQ_TIMEOUT,
                                headers=REQ_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", [])
                return [item[0] for item in result
                        if isinstance(item, (list, tuple)) and len(item) > 0]
        except Exception:
            time.sleep(1)
    return []


def fetch_pdd_hot_search(retries=2):
    """拼多多首页热搜词 — ✅ 从HTML嵌入式JSON提取20个热搜"""
    for _ in range(retries):
        try:
            resp = requests.get("https://mobile.yangkeduo.com/",
                                headers=MOBILE_UA, timeout=REQ_TIMEOUT)
            if resp.status_code != 200:
                continue
            html = resp.text

            # 提取 searchHotQueryRaw 嵌入式 JSON
            start = html.find('searchHotQueryRaw')
            if start < 0:
                continue
            brace_start = html.find('{', start)
            if brace_start < 0:
                continue

            depth = 0
            end = brace_start
            for i, c in enumerate(html[brace_start:]):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = brace_start + i + 1
                        break

            data = json.loads(html[brace_start:end])
            hotqs = data.get('hotqs', [])
            return [item['q'] for item in hotqs if 'q' in item]
        except Exception:
            time.sleep(1)
    return []


def fetch_douyin_hot_search(retries=2):
    """抖音热搜榜 API — ✅ 返回50个热搜词"""
    url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    headers = {
        **REQ_HEADERS,
        "Referer": "https://www.douyin.com/"
    }
    for _ in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                word_list = data.get("data", {}).get("word_list", [])
                return [item.get("word", "") for item in word_list
                        if isinstance(item, dict)]
        except Exception:
            time.sleep(1)
    return []


# ===================== 种子词库 =====================

DEFAULT_SEEDS = {
    "中老年女装": [
        "中老年女装", "妈妈装", "奶奶装", "中老年夏装",
        "中老年春秋装", "中老年冬装", "大码中老年", "胖妈妈装",
    ],
    "套装": [
        "妈妈装套装", "中老年套装", "运动套装女", "休闲套装",
        "冰丝套装", "夏季套装", "两件套",
    ],
    "风格款式": [
        "唐装女", "改良旗袍", "新中式女装", "真丝连衣裙",
        "阔腿裤", "雪纺衫", "宽松衬衫",
        "民族风女装", "国风女装",
    ],
    "功能卖点": [
        "显瘦妈妈装", "遮肚腩", "宽松大码", "纯棉女装",
        "冰丝夏装", "防紫外线", "不缩水", "高档妈妈装",
    ],
    "场景": [
        "广场舞服装", "婚庆妈妈装", "聚会连衣裙",
        "休闲居家套装", "旅游拍照",
    ],
}

# ===================== 清洗 & 交叉验证 =====================


def is_fashion_word(word):
    """判断是否为服装相关词"""
    if not re.search(r'[\u4e00-\u9fff]', word):
        return False
    if NON_FASHION.search(word):
        return False
    if FASHION_FILTER.search(word):
        return True
    # 包含常见的服装概念但不含上述关键词的
    fashion_hints = ['新款', '爆款', '热销', '夏', '春', '秋', '冬',
                     '时尚', '潮流', '简约', '气质', '优雅', '韩版',
                     '宽松', '修身', '显瘦', '大码', '加肥', '加大',
                     '中老年', '妈妈', '奶奶', '阿姨', '老年']
    return any(hint in word for hint in fashion_hints)


def clean_words(words_list):
    """清洗：去空去短、过滤非服装词"""
    cleaned = []
    for w in words_list:
        w = w.strip()
        if len(w) < 2:
            continue
        if not re.search(r'[\u4e00-\u9fff]', w):
            continue
        cleaned.append(w)
    return cleaned


def cross_validate(platform_words):
    """
    输入: {platform: [word, ...]}
    输出: {word: {"platforms": [...], "count": N, "is_cross": bool}}
    
    匹配策略（2层）：
    1. 精确匹配 — 词完全一样
    2. 模糊匹配 — 短词（PDD/3-6字）作为子串出现在长词（TB/DY）中
    """
    tracker = defaultdict(set)
    platform_lists = {
        p: [w.strip() for w in words if len(w.strip()) >= 2]
        for p, words in platform_words.items()
    }

    # 第1层：精确匹配
    for platform, words in platform_lists.items():
        for w in words:
            tracker[w].add(platform)

    # 第2层：模糊匹配（短词作为子串）
    # 收集所有短词（PDD/其他平台的2-6字词）
    short_words = {}
    for platform, words in platform_lists.items():
        for w in words:
            if 2 <= len(w) <= 6:
                short_words.setdefault(w, set()).add(platform)

    # 收集所有长词（TB/DY的6+字词）
    long_words = {}
    for platform, words in platform_lists.items():
        for w in words:
            if len(w) >= 6:
                long_words.setdefault(w, set()).add(platform)

    # 模糊匹配：短词出现在长词中 = 交叉
    for short_word, short_platforms in short_words.items():
        matched_platforms = set(short_platforms)
        for long_word, long_platforms in long_words.items():
            if short_word in long_word:
                matched_platforms.update(long_platforms)
        # 更新追踪器
        if short_word not in tracker:
            tracker[short_word] = set()
        tracker[short_word].update(matched_platforms)
        # 反方向：长词获得短词平台标记
        for long_word, long_platforms in long_words.items():
            if short_word in long_word:
                if long_word not in tracker:
                    tracker[long_word] = set()
                tracker[long_word].update(short_platforms)

    return {
        word: {
            "platforms": sorted(p_set),
            "count": len(p_set),
            "is_cross": len(p_set) >= 2,
        }
        for word, p_set in tracker.items()
    }


# ===================== 主采集流程 =====================


def collect_hot_words(seeds, platforms=None, top=50, cross_only=False, recursive=False):
    """
    完整采集流程：
    1. 淘宝 suggest（10词/种子，可选递归）
    2. 拼多多热搜（20个热搜词）
    3. 抖音热搜榜（50个热搜词）
    4. 合并 → 去重 → 清洗 → 交叉验证
    """
    if platforms is None:
        platforms = ["taobao", "pdd", "douyin"]

    # 存储每个来源的词
    raw_platform_words = defaultdict(list)
    platform_stats = {}

    # ====== 1. 淘宝 suggest ======
    if "taobao" in platforms:
        print("  📡 淘宝 suggest API...")
        score = 0
        for idx, kw in enumerate(seeds):
            words = fetch_taobao_suggest(kw)
            if words:
                clean = clean_words(words)
                raw_platform_words["淘宝"].extend(clean)
                score += len(clean)
                print(f"    [{idx+1}/{len(seeds)}] '{kw}' → {len(clean)} 词")
                time.sleep(0.3)
            else:
                print(f"    [{idx+1}/{len(seeds)}] '{kw}' → 无结果")

        platform_stats["淘宝"] = score
        print(f"    ✅ 淘宝 suggest 共 {score} 个词")

        # 递归展开：取 suggest 结果中服装相关的作新种子再采一轮
        if recursive and score > 0:
            round2_seeds = [
                w for w in list(dict.fromkeys(raw_platform_words["淘宝"]))
                if is_fashion_word(w)
            ][:15]  # 限制最多15个
            if round2_seeds:
                print(f"\n    🔄 递归展开（{len(round2_seeds)} 个服装相关词作新种子）...")
                round2_count = 0
                for idx, kw in enumerate(round2_seeds):
                    words = fetch_taobao_suggest(kw)
                    if words:
                        clean = clean_words(words)
                        raw_platform_words["淘宝"].extend(clean)
                        round2_count += len(clean)
                        if idx < 5 or len(clean) > 0:
                            print(f"      [{idx+1}/{len(round2_seeds)}] '{kw}' → {len(clean)} 词")
                        time.sleep(0.3)
                platform_stats["淘宝"] = score + round2_count
                print(f"    ✅ 递归展开 +{round2_count} 词，淘宝总计 {score + round2_count} 个词")

    # ====== 2. 拼多多热搜 ======
    if "pdd" in platforms:
        print("  📡 拼多多首页热搜...")
        hot = fetch_pdd_hot_search()
        if hot:
            clean = clean_words(hot)
            raw_platform_words["拼多多"].extend(clean)
            platform_stats["拼多多"] = len(clean)
            print(f"    ✅ 共 {len(clean)} 个热搜词: {clean[:10]}...")
        else:
            platform_stats["拼多多"] = 0
            print("    ⚠️ 获取失败")

    # ====== 3. 抖音热搜榜 ======
    if "douyin" in platforms:
        print("  📡 抖音热搜榜...")
        hot = fetch_douyin_hot_search()
        if hot:
            clean = clean_words(hot)
            raw_platform_words["抖音"].extend(clean)
            platform_stats["抖音"] = len(clean)
            print(f"    ✅ 共 {len(clean)} 个热搜词")
        else:
            platform_stats["抖音"] = 0
            print("    ⚠️ 获取失败")

    # ====== 交叉验证 ======
    print("\n  ⚡ 交叉验证...")
    cross_result = cross_validate(dict(raw_platform_words))

    all_words = []
    cross_words = []
    for word, info in cross_result.items():
        entry = {
            "word": word,
            "platforms": info["platforms"],
            "count": info["count"],
            "is_cross": info["is_cross"],
        }
        all_words.append(entry)
        if info["is_cross"]:
            cross_words.append(entry)

    # 排序：跨平台优先 → 出现平台数降序 → 词长降序
    all_words.sort(key=lambda x: (-x["count"], -len(x["word"])))
    cross_words.sort(key=lambda x: (-x["count"], -len(x["word"])))

    total_unique = len(all_words)
    cross_unique = len(cross_words)
    total_raw = sum(len(w) for w in raw_platform_words.values())

    result = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seed_count": len(seeds),
            "platforms": platforms,
            "recursive": recursive,
            "total_raw": total_raw,
            "total_unique": total_unique,
            "cross_platform_count": cross_unique,
            "cross_ratio": round(cross_unique / max(total_unique, 1) * 100, 1),
        },
        "platform_stats": platform_stats,
        "cross_validated": cross_words[:top],
        "all_words": all_words[:top],
        "all_words_detail": all_words,
    }

    if cross_only:
        result["hot_words"] = result["cross_validated"]
    else:
        result["hot_words"] = result["all_words"]

    return result


# ===================== CLI =====================


def main():
    parser = argparse.ArgumentParser(
        description="电商热搜词采集工具 v2.0 — 三大平台交叉验证",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python collect_hot_words.py                                  # 默认采集
  python collect_hot_words.py --cross-only                      # 仅跨平台词
  python collect_hot_words.py --recursive                       # 递归展开suggest
  python collect_hot_words.py --seeds "连衣裙,卫衣" --top 30
  python collect_hot_words.py --platforms taobao,douyin
  python collect_hot_words.py --output ./hot_words.json
        """,
    )
    parser.add_argument("--seeds", type=str,
                        help="种子词，逗号分隔")
    parser.add_argument("--seeds-file", type=str,
                        help="种子词文件（每行一个词）")
    parser.add_argument("--platforms", type=str, default="taobao,pdd,douyin",
                        help="目标平台（逗号分隔，默认所有）")
    parser.add_argument("--top", type=int, default=50,
                        help="返回前N个词（默认50）")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="递归展开：suggest结果作新种子再采一轮")
    parser.add_argument("--cross-only", "-c", action="store_true",
                        help="仅显示跨2+平台验证的词")
    parser.add_argument("--output", "-o", type=str, default="",
                        help="输出JSON文件路径")
    parser.add_argument("--output-json", type=str, default="",
                        help="输出热词JSON结果到文件（供pipeline.py读取）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细过程")

    args = parser.parse_args()

    # 种子词
    if args.seeds:
        seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    elif args.seeds_file:
        try:
            with open(args.seeds_file, "r", encoding="utf-8") as f:
                seeds = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ 种子词文件不存在: {args.seeds_file}")
            sys.exit(1)
    else:
        seeds = []
        for cat, words in DEFAULT_SEEDS.items():
            seeds.extend(words)

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    top_n = min(max(args.top, 5), 200)

    plat_names = {"taobao": "淘宝", "pdd": "拼多多", "douyin": "抖音"}
    plat_display = [plat_names.get(p, p) for p in platforms]

    print(f"{'='*55}")
    print(f"🔍 电商热搜词采集 v2.0")
    print(f"{'='*55}")
    print(f"  种子词: {len(seeds)} 个")
    print(f"  平台: {', '.join(plat_display)}")
    print(f"  模式: {'仅跨平台' if args.cross_only else '全量'}"
          f"{' + 递归展开' if args.recursive else ''}")
    print(f"  目标: 前 {top_n} 个词")
    print(f"{'='*55}")

    start_ts = time.time()
    result = collect_hot_words(seeds, platforms, top_n,
                               cross_only=args.cross_only,
                               recursive=args.recursive)
    elapsed = time.time() - start_ts

    data_source = result["cross_validated"] if args.cross_only else result["all_words"]

    print(f"\n{'='*55}")
    print(f"📊 采集报告")
    print(f"{'='*55}")
    print(f"  原始词总量: {result['meta']['total_raw']}")
    print(f"  去重后: {result['meta']['total_unique']} 个")
    print(f"  跨平台验证: {result['meta']['cross_platform_count']} 个 "
          f"({result['meta']['cross_ratio']}%)")
    print(f"  耗时: {elapsed:.1f}s")
    print(f"\n  各平台:")
    for k, v in result["platform_stats"].items():
        if v > 0:
            print(f"    {k}: {v} 个词")

    print(f"\n{'─'*55}")
    if args.cross_only:
        print(f"🔥 跨平台高置信词 ({len(data_source)} 个):")
    else:
        print(f"🔥 TOP {min(top_n, len(data_source))} 热词:")
    print(f"{'─'*55}")

    for i, item in enumerate(data_source[:20]):
        plat_str = ", ".join(item["platforms"])
        tag = " 🔀" if item["is_cross"] else ""
        print(f"  #{i+1:3d}  {item['word']:<22s} [{item['count']}平台] {tag}")

    if len(data_source) > 20:
        print(f"  ... 还有 {len(data_source) - 20} 个词 (--top {top_n})")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存到: {args.output}")

    if args.output_json:
        output_data = {"hot_words": data_source, "meta": result["meta"]}
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 热词结果已输出到: {args.output_json}")
    else:
        print(f"\n📋 完整JSON:")
        for item in data_source:
            print(f"  {json.dumps(item, ensure_ascii=False)}")

    print(f"\n⏱ 耗时: {elapsed:.1f}s  |  跨平台率: {result['meta']['cross_ratio']}%")


if __name__ == "__main__":
    main()

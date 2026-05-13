#!/usr/bin/env python3
"""内容推送后处理 — 审核+图表+封面+草稿箱推送
用法: python3 publish_pipeline.py --file article.md --title "标题" --domain daily|weekly|kepu
输出: JSON {"review": {...}, "charts": [...], "draft_id": "..."}
"""
import os, sys, json, subprocess, re, io, requests
from pathlib import Path
from datetime import datetime

TOOLS = Path("/home/pebynn/tools")
QUANT_PY = str(TOOLS / "quant_env" / "bin" / "python3")

# ── Tier1 AI洗词 ──
BAN_WORDS = [
    "强势反弹","大举扫货","全线飘红","赚钱效应","宽幅震荡","结构性行情",
    "投资者可关注","从技术面看","建议关注","投资者需","展望后市","总体来看",
    "整体而言","在这一背景下","值得一提的是","值得注意的是","综上所述","由此可见",
    "不容忽视","值得期待","引发市场关注","备受瞩目","迎来","掀起","引爆",
    "主力资金","北向资金大幅","抄底","逃顶","放量","缩量","企稳","筑底",
    "龙头","妖股","金叉","死叉","突破","回踩","支撑位","压力位",
]
AI_SENTENCE_PATTERNS = [
    r'从.{1,10}来看',
    r'值得.{1,5}的是',
    r'不难发现',
    r'可以看到',
    r'这意味着',
    r'这反映出',
]

# ── Review ──
def review_article(content: str) -> dict:
    """对文章进行质量审核"""
    issues = []
    warnings = []
    
    # AI词检测
    found_ban = []
    for w in BAN_WORDS:
        if w in content:
            found_ban.append(w)
    if found_ban:
        issues.append(f"AI套话: {', '.join(found_ban)}")
    
    # AI句式检测
    for pat in AI_SENTENCE_PATTERNS:
        m = re.findall(pat, content)
        if len(m) > 2:
            warnings.append(f"AI句式重复({len(m)}次): {pat}")
    
    # 字数检查
    word_count = len(content.replace('\n','').replace(' ',''))
    if word_count < 500:
        issues.append(f"字数不足: {word_count}字")
    
    # 风险提示检查
    if "投资" in content and "风险" not in content:
        warnings.append("含投资内容但缺少风险提示")
    
    # 图表引用检查
    has_chart = bool(re.search(r'!\[.*\]\(.*\.(png|jpg)\)', content))
    
    verdict = "BLOCK" if issues else ("WARN" if warnings else "APPROVED")
    return {
        "verdict": verdict,
        "issues": issues,
        "warnings": warnings,
        "stats": {"words": word_count, "has_chart_ref": has_chart},
    }


# ── Charts ──
def generate_charts(title: str, domain: str, output_dir: str) -> list:
    """生成金融科普配图"""
    charts = []
    os.makedirs(output_dir, exist_ok=True)
    
    script = f'''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 中文字体
for f in fm.fontManager.ttflist:
    if 'Noto Sans CJK' in f.name or 'WenQuanYi' in f.name or 'DroidSans' in f.name:
        plt.rcParams['font.sans-serif'] = [f.name] + plt.rcParams['font.sans-serif']
        break
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 200

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), facecolor='#0d1117')
for ax in (ax1, ax2):
    ax.set_facecolor('#0d1117')
    ax.tick_params(colors='white', labelsize=10)
    ax.spines['bottom'].set_color('#444')
    ax.spines['left'].set_color('#444')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

# 左图: K线结构示意
from matplotlib.patches import Rectangle, FancyBboxPatch
# 阳线
ax1.add_patch(Rectangle((1, 100), 0.6, 5, facecolor='#D32F2F', edgecolor='#D32F2F'))
ax1.plot([1.3, 1.3], [99, 100], color='#D32F2F', linewidth=1)  # 下影
ax1.plot([1.3, 1.3], [105, 107], color='#D32F2F', linewidth=1)  # 上影
# 阴线
ax1.add_patch(Rectangle((3, 102), 0.6, 4, facecolor='#388E3C', edgecolor='#388E3C'))
ax1.plot([3.3, 3.3], [100, 102], color='#388E3C', linewidth=1)
ax1.plot([3.3, 3.3], [106, 108], color='#388E3C', linewidth=1)
# 标注
ax1.text(1.3, 108, '上影线', color='white', fontsize=9, ha='center')
ax1.text(1.3, 96, '下影线', color='white', fontsize=9, ha='center')
ax1.text(3.3, 109, '上影线', color='white', fontsize=9, ha='center')
ax1.text(3.3, 98, '下影线', color='white', fontsize=9, ha='center')
ax1.set_title('红涨绿跌', color='white', fontsize=14, pad=10)
ax1.set_xlim(0, 5)
ax1.set_ylim(95, 115)
ax1.axis('off')

# 右图: 均线示意
np.random.seed(42)
n = 60
close = 100 + np.cumsum(np.random.randn(n) * 0.8)
ma5 = np.convolve(close, np.ones(5)/5, mode='valid')
ma20 = np.convolve(close, np.ones(20)/20, mode='valid')
x_all = np.arange(n)
ax2.plot(x_all, close, color='#aaa', linewidth=0.8, alpha=0.5)
ax2.plot(np.arange(len(ma5)), ma5 + close[4] - ma5[0], color='#FFB74D', linewidth=1.5, label='5日')
ax2.plot(np.arange(len(ma20)), ma20 + close[19] - ma20[0], color='#64B5F6', linewidth=1.5, label='20日')
ax2.legend(frameon=False, fontsize=9, labelcolor='white')
ax2.set_title('移动平均线', color='white', fontsize=14, pad=10)
ax2.set_ylabel('价格', color='white')
fig.suptitle('{title[:20]}', color='white', fontsize=12, y=0.98)
plt.tight_layout()
plt.savefig("{output_dir}/chart_kline.png", dpi=200, bbox_inches='tight', facecolor='#0d1117')
plt.close()
print("OK: chart_kline.png")
'''
    try:
        r = subprocess.run(
            [QUANT_PY, "-c", script],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "HOME": str(Path.home())}
        )
        if "OK:" in r.stdout:
            charts.append(f"{output_dir}/chart_kline.png")
    except Exception as e:
        print(f"Chart generation failed: {e}", file=sys.stderr)
    
    return charts


# ── WeChat Push ──
def push_to_wechat(filepath: str, title: str, charts: list, cover_title: str) -> dict:
    """推送到微信公众号草稿箱"""
    # 读取文章
    raw_content = Path(filepath).read_text()
    # 如果有图表但文中无引用，追加图表引用
    content = raw_content
    if charts:
        for chart_path in charts:
            fname = Path(chart_path).name
            if fname not in raw_content:
                content += f"\n\n![配图]({chart_path})\n"
    if content != raw_content:
        Path(filepath).write_text(content)
    
    # 获取access_token
    env_file = Path.home() / ".hermes" / ".env"
    secret = ""
    if env_file.exists():
        for l in env_file.read_text().split("\n"):
            if l.startswith("WECHAT_APP_SECRET="):
                secret = l.split("=",1)[1].strip().strip('"').strip("'")
    if not secret:
        return {"error": "WECHAT_APP_SECRET not found"}
    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type":"client_credential","appid":"wx9776210069a7a9a0","secret":secret},
        timeout=15
    )
    token_data = resp.json()
    if "access_token" not in token_data:
        return {"error": str(token_data)}
    token = token_data["access_token"]
    
    # 上传文章内图片到微信CDN
    cdn_map = {}
    for chart_path in charts:
        if Path(chart_path).exists():
            try:
                with open(chart_path, 'rb') as f:
                    img_resp = requests.post(
                        "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
                        params={"access_token": token},
                        files={"media": (Path(chart_path).name, f, "image/png")},
                        timeout=30
                    )
                img_data = img_resp.json()
                if "url" in img_data:
                    cdn_map[chart_path] = img_data["url"]
            except Exception as e:
                print(f"Image upload failed for {chart_path}: {e}", file=sys.stderr)
    
    # 替换本地路径为CDN URL并更新文件
    for local_path, cdn_url in cdn_map.items():
        content = content.replace(local_path, cdn_url)
    if cdn_map:
        Path(filepath).write_text(content)
    
    # 找标题
    if not title:
        for line in content.strip().split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
    if not title:
        title = Path(filepath).stem
    
    # Markdown → HTML
    html_parts = ['<html><body>']
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2 style=\"color:#FF6600\">{line[3:]}</h2>")
        elif line.startswith("### "):
            html_parts.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("**") and line.endswith("**"):
            html_parts.append(f"<p><strong>{line[2:-2]}</strong></p>")
        elif line.startswith("![") and "](" in line and line.endswith(")"):
            alt = line[2:line.index("](")]
            src = line[line.index("](")+2:-1]
            html_parts.append(f'<p><img src="{src}" alt="{alt}"/></p>')
        elif line == "---":
            html_parts.append("<hr/>")
        elif line.startswith("- ") or line.startswith("* "):
            html_parts.append(f"<li>{line[2:]}</li>")
        else:
            html_parts.append(f"<p>{line}</p>")
    html_parts.append("</body></html>")
    html = "\n".join(html_parts)
    
    # 上传封面图
    cover_r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "wechat_cover.py"), "--title", cover_title],
        capture_output=True, text=True, timeout=30
    )
    try:
        cover_info = json.loads(cover_r.stdout)
        thumb_id = cover_info.get("thumb_media_id", "")
    except:
        thumb_id = ""
    if not thumb_id:
        return {"error": "Failed to upload cover image"}
    
    # 推送草稿
    body = {
        "articles": [{
            "title": title[:64],
            "author": "AI财经",
            "digest": content[:100].replace("\n"," ")[:120],
            "content": html,
            "thumb_media_id": thumb_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "is_aigc": 1,
        }]
    }
    body_json = json.dumps(body, ensure_ascii=False)
    resp = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": token},
        data=body_json.encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30
    )
    result = resp.json()
    return {
        "draft_id": result.get("media_id", ""),
        "error": "" if "media_id" in result else str(result),
        "charts_count": len(charts),
        "cdn_images": len(cdn_map),
    }


# ── Main ──
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Markdown文件路径")
    ap.add_argument("--title", default="", help="文章标题")
    ap.add_argument("--domain", default="daily", choices=["daily","weekly","kepu","event"])
    ap.add_argument("--push", action="store_true", default=True, help="推送到微信草稿箱")
    ap.add_argument("--no-push", dest="push", action="store_false")
    args = ap.parse_args()
    
    filepath = Path(args.file)
    if not filepath.exists():
        print(json.dumps({"error": f"File not found: {args.file}"}))
        sys.exit(1)
    
    content = filepath.read_text()
    
    # 1. Review
    review = review_article(content)
    
    # 2. Charts
    date_str = datetime.now().strftime("%Y-%m-%d")
    chart_dir = f"/home/pebynn/writing-data/charts/{date_str}"
    charts = generate_charts(args.title or filepath.stem, args.domain, chart_dir)
    
    # 3. Push
    result = {"review": review, "charts": charts}
    if args.push:
        push_result = push_to_wechat(str(filepath), args.title, charts, args.title or "A股财经")
        result["push"] = push_result
    
    print(json.dumps(result, ensure_ascii=False))

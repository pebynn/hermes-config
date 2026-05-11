#!/usr/bin/env python3
"""
电商图片批量处理流水线
功能：去水印 → AI抠图换背景 → 去重 → 加文案 → 输出

用法：
    # 基本用法：处理一个目录里的所有图片
    python batch_edit_images.py --input ./raw_images --output ./processed

    # 只去水印（不做抠图）
    python batch_edit_images.py --input ./raw --output ./clean --mode nowm

    # 完整流水线（去水印+抠图+去重）
    python batch_edit_images.py --input ./raw --output ./final --mode full

    # 加卖点文案
    python batch_edit_images.py --input ./clean --output ./with_text --add-text

    # 自定义文案
    python batch_edit_images.py --input ./raw --output ./done --texts \
        "宽松大码,100,50" "纯棉透气,100,100" "妈妈装爆款,100,150"
"""

import os
import sys
import argparse
import hashlib
import json
import time
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ 需要 Pillow: pip install Pillow")
    sys.exit(1)

try:
    import cv2
    import numpy as np
except ImportError:
    print("❌ 需要 opencv-python: pip install opencv-python")
    sys.exit(1)

# ===================== 工具函数 =====================

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def list_images(input_dir):
    """列出目录下所有图片文件"""
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    files = []
    for f in sorted(os.listdir(input_dir)):
        if os.path.splitext(f)[1].lower() in exts:
            files.append(os.path.join(input_dir, f))
    print(f"  📷 找到 {len(files)} 张图片")
    return files


# ===================== 去水印 =====================

def remove_watermark(image_path, output_path, roi=None, method="inpaint"):
    """
    去除水印
    roi: (x, y, w, h) 水印区域坐标，None=自动检测右下角
    method: "inpaint"（修复）或 "clone"（克隆填充）
    """
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"    ⚠️ 无法读取: {image_path}")
        return False

    h, w = img.shape[:2]

    if roi is None:
        # 默认：右下角 120x70 区域
        x1 = max(0, w - 130)
        y1 = max(0, h - 80)
        x2, y2 = w - 5, h - 5
    else:
        x, y, rw, rh = roi
        x1, y1 = x, y
        x2, y2 = min(x + rw, w), min(y + rh, h)

    if method == "inpaint":
        # 用 OpenCV inpainting 修复水印区域
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
        result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    else:
        # 克隆填充：用上方相邻区域覆盖
        roi_h = y2 - y1
        fill_region = img[max(0, y1 - roi_h):y1, x1:x2].copy()
        if fill_region.shape[0] > 0:
            fill_h = min(fill_region.shape[0], roi_h)
            img[y1:y1 + fill_h, x1:x2] = fill_region[:fill_h, :]
        result = img

    cv2.imwrite(str(output_path), result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return True


# ===================== AI抠图 =====================

def remove_background(input_path, output_path, bg_color=(255, 255, 255)):
    """用 rembg 抠图并替换背景"""
    try:
        from rembg import remove as rembg_remove
    except ImportError:
        print("    ⚠️ rembg 未安装，跳过抠图")
        print("      安装: pip install rembg")
        return False

    try:
        with open(input_path, "rb") as f:
            input_data = f.read()

        output_data = rembg_remove(input_data)
        subject = Image.open(io.BytesIO(output_data)).convert("RGBA")
        bg = Image.new("RGBA", subject.size, (*bg_color, 255))
        bg.paste(subject, (0, 0), subject)
        bg.convert("RGB").save(output_path, quality=95)
        return True
    except Exception as e:
        print(f"    ⚠️ 抠图失败: {e}")
        return False


# ===================== MD5去重（微像素扰动） =====================

def md5_obfuscate(image_path, output_path):
    """
    通过微小像素变化改变文件MD5，视觉上无差别
    防平台「图片同款」检测
    """
    img = Image.open(image_path).convert("RGB")
    pixels = img.load()
    w, h = img.size

    # 改动策略：角落+边缘+中间各改1个像素
    modifications = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, h // 2), (w // 3, h // 3)
    ]
    for x, y in modifications:
        try:
            r, g, b = pixels[x, y]
            pixels[x, y] = (min(r + 1, 255), max(g - 1, 0), b)
        except:
            pass

    img.save(str(output_path), quality=92)
    return True


# ===================== 加文案 =====================

def find_chinese_font():
    """查找系统中可用的中文字体"""
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return fp
    return None


def add_text_overlay(image_path, output_path, texts, font_size=36, font_color=(255, 0, 0)):
    """
    在主图上叠加卖点文案
    texts: [{"text": "文案", "pos": (x, y)}, ...]
    """
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    font_path = find_chinese_font()
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    for t in texts:
        text = t.get("text", "")
        pos = t.get("pos", (50, 50))
        color = t.get("color", font_color)
        size = t.get("size", font_size)

        if size != font_size and font_path:
            try:
                font = ImageFont.truetype(font_path, size)
            except:
                pass

        # 描边效果（白底黑字更有质感）
        stroke_color = (255, 255, 255)
        draw.text(pos, text, fill=(*color, 220), font=font,
                  stroke_width=2, stroke_fill=(*stroke_color, 200))

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(str(output_path), quality=92)
    return True


# ===================== 批量处理流水线 =====================

def run_full_pipeline(input_dir, output_dir, mode="full", add_text=False, texts=None):
    """
    完整流水线
    mode: "nowm"（只去水印）| "full"（全套）
    """
    ensure_dir(output_dir)
    images = list_images(input_dir)
    stats = {"total": len(images), "processed": 0, "skipped": 0, "failed": 0}

    for idx, img_path in enumerate(images):
        fname = os.path.basename(img_path)
        base, ext = os.path.splitext(fname)
        print(f"\n  [{idx + 1}/{len(images)}] {fname}")

        try:
            # Step 1: 去水印
            step1 = os.path.join(output_dir, f"{base}_step1{ext}")
            if not remove_watermark(img_path, step1):
                stats["failed"] += 1
                continue
            current = step1

            if mode == "full":
                # Step 2: 抠图换背景
                step2 = os.path.join(output_dir, f"{base}_step2{ext}")
                if remove_background(current, step2, bg_color=(255, 255, 255)):
                    os.remove(current)
                    current = step2
                else:
                    print(f"    ⚠️ 抠图跳过，使用去水印后的图继续")

                # Step 3: MD5去重
                final = os.path.join(output_dir, f"{base}_final{ext}")
                md5_obfuscate(current, final)
                if current != os.path.join(output_dir, f"{base}_step1{ext}"):
                    os.remove(current)

                # Step 4: 加文案（可选）
                if add_text and texts:
                    text_final = os.path.join(output_dir, f"{base}_text{ext}")
                    add_text_overlay(final, text_final, texts)
                    os.remove(final)
                    final = text_final
            else:
                # 仅去水印模式
                final = os.path.join(output_dir, f"{base}_nowm{ext}")
                os.rename(current, final)
                if add_text and texts:
                    text_final = os.path.join(output_dir, f"{base}_text{ext}")
                    add_text_overlay(final, text_final, texts)
                    os.remove(final)
                    final = text_final

            # 验证
            fsize = os.path.getsize(final)
            print(f"    ✅ 完成: {os.path.basename(final)} ({fsize / 1024:.1f}KB)")
            stats["processed"] += 1

        except Exception as e:
            print(f"    ❌ 失败: {e}")
            stats["failed"] += 1

    # 输出统计
    print(f"\n{'='*40}")
    print(f"📊 处理统计")
    print(f"{'='*40}")
    print(f"  总计: {stats['total']} 张")
    print(f"  成功: {stats['processed']} 张")
    print(f"  失败: {stats['failed']} 张")
    print(f"  输出目录: {output_dir}")
    print(f"{'='*40}")

    return stats


# ===================== CLI 入口 =====================

def main():
    parser = argparse.ArgumentParser(
        description="批量电商图片处理流水线 - 去水印/抠图/去重/加文案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python batch_edit_images.py -i ./raw -o ./processed
  python batch_edit_images.py -i ./raw -o ./clean --mode nowm
  python batch_edit_images.py -i ./raw -o ./final --add-text
  python batch_edit_images.py -i ./raw -o ./done --texts "爆款推荐,50,50" "限时特价,50,120"
        """
    )
    parser.add_argument("-i", "--input", required=True, help="输入图片目录")
    parser.add_argument("-o", "--output", required=True, help="输出图片目录")
    parser.add_argument("-m", "--mode", choices=["nowm", "full"], default="full",
                        help="处理模式: nowm(只去水印) / full(全套,默认)")
    parser.add_argument("--add-text", action="store_true",
                        help="是否加卖点文案")
    parser.add_argument("--texts", nargs="*",
                        help="文案列表，格式: '文案内容,x坐标,y坐标' 如 '宽松大码,50,50'")
    parser.add_argument("--bg-color", default="255,255,255",
                        help="抠图后背景色 RGB (默认白色)")

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"❌ 输入目录不存在: {args.input}")
        sys.exit(1)

    # 解析文案
    texts = []
    if args.texts:
        for t in args.texts:
            parts = t.split(",")
            if len(parts) >= 3:
                texts.append({
                    "text": parts[0],
                    "pos": (int(parts[1]), int(parts[2])),
                    "color": (255, 0, 0) if "特价" in parts[0] or "爆款" in parts[0] else (0, 0, 0),
                    "size": 48 if "特价" in parts[0] else 36
                })
    elif args.add_text:
        # 默认文案
        texts = [
            {"text": "爆款推荐", "pos": (50, 50), "color": (255, 0, 0), "size": 48},
            {"text": "限时特价", "pos": (50, 120), "color": (255, 50, 50), "size": 36},
            {"text": "品质保证", "pos": (50, 190), "color": (0, 120, 0), "size": 30},
        ]

    print(f"{'='*50}")
    print(f"🖼️  电商图片批量处理流水线")
    print(f"{'='*50}")
    print(f"  📂 输入: {args.input}")
    print(f"  📂 输出: {args.output}")
    print(f"  ⚙️  模式: {args.mode}")
    print(f"  ✏️  加文案: {'是 ({})'.format(len(texts)) if texts else '否'}")
    print(f"{'='*50}")

    run_full_pipeline(args.input, args.output, args.mode, bool(texts), texts)


if __name__ == "__main__":
    import io  # for rembg BytesIO handling
    main()

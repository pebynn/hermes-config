# 封面图 PIL 降级方案 (2026-05-10)

## 背景

matplotlib 不可用时（PEP 668 封锁 + `--break-system-packages` 风险），微信草稿箱 API 需要 `thumb_media_id` 否则返回 `[40007] invalid media_id`。

## 方案

`publish_draft.py` 新增 `_create_cover_pil()` 函数：

```python
def _create_cover_pil(date_str: str, draft_type: str = "daily") -> Optional[str]:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (900, 500), '#1a1a2e')
    draw = ImageDraw.Draw(img)
    # 查找中文字体
    font = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 36)
    # 按类型生成标题
    draw.text((50, 70), title, fill='#e94560', font=font)
    img.save(str(charts_cover / 'cover.png'))
    return str(path)
```

## 调用链

```
create_cover_image() 
  → 先检查现有 cover.png
  → 尝试 matplotlib
  → ImportError → _create_cover_pil()
  → upload_image_to_wechat() → 得 thumb_media_id
  → push_to_wechat_draft(thumb_media_id=...)
```

## 字体路径优先级

1. `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`
2. `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
3. `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
4. `ImageFont.load_default()`（兜底，无中文）

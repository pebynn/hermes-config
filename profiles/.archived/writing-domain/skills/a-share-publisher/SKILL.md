---
name: a-share-publisher
description: A股复盘文章发布技能 - 将复盘文章同步到微信公众号草稿箱
version: 1.0.0
author: Hermes
license: MIT
related_skills: [a-share-review-writer]
scripts: [publish_draft.py]
---

# A股复盘文章发布技能

将a-share-review-writer生成的复盘文章，通过微信公众号API创建草稿箱，等待人工审核后发布。

---

## 触发条件

- a-share-review-writer产出复盘草稿后
- 用户主动请求："发布今日复盘到草稿箱"
- 域主代理编排调度

---

## 执行流程

### Step 1: 读取复盘草稿
1. 读取 ~/writing-data/drafts/YYYY-MM-DD-每日复盘.md
2. 解析内容结构：
   - 标题（# 标题行）
   - 正文（各章节内容）
   - 元数据（生成时间/模型/数据源等）

### Step 2: 验证内容完整性
- [ ] 标题存在且不为空
- [ ] 正文≥1000字
- [ ] 五大章节完整（大盘/资金/热点/技术/策略）
- [ ] 风险提示存在
- [ ] AIGC标识存在
- [ ] 元数据完整

### Step 3: 转换为HTML格式
```python
# Markdown→微信公众号HTML
import re

def md_to_wechat_html(md_text):
    lines = md_text.split('\n')
    html_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            html_parts.append('<p><br/></p>')
        elif line.startswith('# '):
            html_parts.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_parts.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_parts.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('- '):
            html_parts.append(f'<p>• {line[2:]}</p>')
        elif line.startswith('1.') or line.startswith('2.'):
            html_parts.append(f'<p>{line}</p>')
        else:
            html_parts.append(f'<p>{line}</p>')

    return ''.join(html_parts)
```

### Step 4: 获取Access Token
```bash
# 检查缓存
if [ -f ~/.hermes/credentials/wechat_access_token.json ]; then
    TOKEN_DATA=$(cat ~/.hermes/credentials/wechat_access_token.json)
    EXPIRES=$(echo $TOKEN_DATA | python3 -c "import sys,json; print(json.load(sys.stdin)['expires_at'])")
    NOW=$(date +%s)

    if [ $NOW -lt $EXPIRES ]; then
        # Token有效
        ACCESS_TOKEN=$(echo $TOKEN_DATA | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    else
        # Token过期，刷新
        RESP=$(curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx9776210069a7a9a0&secret=c7339b44163be2e8424d6d44e29f85e3")
        ACCESS_TOKEN=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
        EXPIRES_IN=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['expires_in'])")
        echo "{\"access_token\": \"$ACCESS_TOKEN\", \"expires_at\": $((NOW + EXPIRES_IN))}" > ~/.hermes/credentials/wechat_access_token.json
    fi
fi
```

### Step 5: 创建草稿
```bash
curl -s -X POST "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=$ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
    "articles": [{
        "title": "【每日复盘】2026-05-05 A股收盘总结",
        "author": "复盘点金",
        "digest": "三大指数集体收涨，北向资金净流入35亿，两市成交额突破万亿...",
        "content": "<p>HTML格式正文...</p>",
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
        "is_aigc": 1
    }]
}'
```

### Step 6: 处理响应
**成功**：
```json
{"errcode": 0, "media_id": "MEDIA_ID"}
```
→ 更新草稿元数据+记录发布日志

**失败**：
| 错误码 | 处理 |
|--------|------|
| 40001 | 刷新Token重试 |
| 45009 | 接口超限，降级为本地保存 |
| 其他 | 降级方案 |

### Step 7: 更新文件状态
**草稿文件新增元数据**：
```markdown
---
## 元数据
- 草稿箱ID: MEDIA_ID
- 发布状态: 已同步到草稿箱
- 同步时间: 2026-05-05 17:00
- 审核提示: 请登录微信公众号审核后发布
---
```

**发布日志**：
```log
[2026-05-05 17:00:00] 复盘草稿同步成功
- 文件: ~/writing-data/drafts/2026-05-05-每日复盘.md
- 草稿箱ID: MEDIA_ID
- 状态: 等待人工审核
- 提醒: 请登录 mp.weixin.qq.com 审核
```

---

## 工具链

| 工具 | 用途 |
|------|------|
| terminal | 调用微信API |
| execute_code | HTML转换逻辑 |
| write_file | 更新草稿+日志 |
| read_file | 读取草稿内容 |

---

## 降级方案

### API不可用时
1. **生成HTML文件**：保存到本地，用户手动粘贴
2. **生成Markdown文件**：用户手动复制到公众号编辑器
3. **输出文字版**：直接在终端显示复盘内容

### 非认证账号限制
仅创建草稿（draft.add），不自动发布。用户需：
1. 登录 https://mp.weixin.qq.com/
2. 进入"草稿箱"
3. 找到复盘文章
4. 审核后发布

---

## 合规要求

### 必含内容
1. **AIGC标识**：`is_aigc: 1` + 文章末尾"本文由AI辅助创作"
2. **风险提示**："以上内容不构成投资建议，股市有风险，投资需谨慎"
3. **原创性**：避免直接复制研报内容

### 合规检查清单
- [ ] is_aigc标记已设置
- [ ] 风险提示已包含
- [ ] 无个股推荐表述
- [ ] 数据来源标注

---

## 发布节奏

| 时间 | 动作 |
|------|------|
| 15:30-16:00 | 数据采集 |
| 16:00-16:30 | 复盘写作 |
| 16:30-17:00 | 排版审核 |
| 17:00 | 同步到草稿箱 |
| 次日开盘前 | 人工审核+发布 |

---

## 输出规范

### 必需输出
- 更新后的草稿文件（含草稿箱ID）
- 发布日志

### 可选输出
- HTML格式预览文件
- 纯文本版复盘（备用）

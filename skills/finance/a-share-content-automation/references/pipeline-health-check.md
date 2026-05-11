# 管线健康检查

## 脚本

`~/.hermes/profiles/writing-domain/skills/a-share-review-writer/scripts/pipeline_health_check.py`

## 用法

```bash
python3 pipeline_health_check.py [--date YYYY-MM-DD]
```

## 检查维度

| 维度 | 检查项 |
|:--|:--|
| 目录结构 | raw/charts/drafts/publish-logs 是否存在 |
| 核心脚本 | 5个脚本文件是否存在 |
| 当日数据 | all_data.json 存在性 + data_completeness + 交叉验证状态 |
| 图表文件 | 6张图表是否存在 + 文件大小 |
| 中文字体 | matplotlib 是否识别 WenQuanYi Zen Hei |
| API连通性 | Sina 指数API（全天可用）+ 东财push2 API（仅白天） |
| 环境变量 | DEEPSEEK_API_KEY + WECHAT_APP_SECRET |

## 使用场景

- 每天 15:30 cron 前运行确认管线就绪
- 手动运行复盘前快速验证
- 故障排查第一步

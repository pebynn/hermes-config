#!/bin/bash
# A股每日复盘写作域快速启动脚本 v2.0
echo "=========================================="
echo "A股每日复盘写作域 - 快速启动"
echo "=========================================="
echo ""

DOMAIN_DIR="$HOME/.hermes/profiles/writing-domain"
DATA_DIR="$HOME/writing-data"

[ ! -d "$DOMAIN_DIR" ] && echo "❌ 域目录不存在: $DOMAIN_DIR" && exit 1
[ ! -d "$DATA_DIR" ] && mkdir -p "$DATA_DIR"/{raw,drafts,publish-logs,analysis,charts}

echo "📋 配置文件: $DOMAIN_DIR/config.yaml"
echo ""

# 检查脚本（5个）
echo "🔍 检查脚本..."
SCRIPTS=(
  "a-share-data-collector/scripts/collect_data.py"
  "a-share-review-writer/scripts/generate_charts.py"
  "a-share-review-writer/scripts/generate_review.py"
  "a-share-review-writer/scripts/weekly_summary.py"
  "a-share-publisher/scripts/publish_draft.py"
)
ALL_OK=true
for s in "${SCRIPTS[@]}"; do
  if [ -f "$DOMAIN_DIR/skills/$s" ]; then
    python3 -c "import py_compile; py_compile.compile('$DOMAIN_DIR/skills/$s', doraise=True)" 2>/dev/null \
      && echo "  ✅ $s" \
      || { echo "  ⚠️ $s (语法错误)"; ALL_OK=false; }
  else
    echo "  ❌ $s (缺失)"
    ALL_OK=false
  fi
done

# 检查依赖
echo ""
echo "🔍 检查Python依赖..."
python3 -c "import akshare" 2>/dev/null && echo "  ✅ akshare" || echo "  ❌ akshare (pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple)"
python3 -c "import matplotlib" 2>/dev/null && echo "  ✅ matplotlib" || echo "  ❌ matplotlib"
python3 -c "import mplfinance" 2>/dev/null && echo "  ✅ mplfinance" || echo "  ❌ mplfinance"
python3 -c "import requests" 2>/dev/null && echo "  ✅ requests" || echo "  ❌ requests"

# 检查环境变量
echo ""
echo "🔑 环境变量..."
[ -n "$DEEPSEEK_API_KEY" ] && echo "  ✅ DEEPSEEK_API_KEY" || echo "  ⚠️ DEEPSEEK_API_KEY (将从.env加载)"
[ -n "$WECHAT_APP_SECRET" ] && echo "  ✅ WECHAT_APP_SECRET" || echo "  ⚠️ WECHAT_APP_SECRET (将从.env加载)"

echo ""
echo "=========================================="
echo "域状态"
echo "=========================================="

if [ "$ALL_OK" = true ]; then
  echo "✅ 域已就绪！"
  echo ""
  echo "📝 命令行使用"
  echo "  python3 $DOMAIN_DIR/skills/a-share-data-collector/scripts/collect_data.py"
  echo "  python3 $DOMAIN_DIR/skills/a-share-review-writer/scripts/generate_charts.py --date \$(date +%F)"
  echo "  python3 $DOMAIN_DIR/skills/a-share-review-writer/scripts/generate_review.py --date \$(date +%F)"
  echo "  python3 $DOMAIN_DIR/skills/a-share-review-writer/scripts/weekly_summary.py"
  echo "  python3 $DOMAIN_DIR/skills/a-share-publisher/scripts/publish_draft.py --check-ip"
  echo ""
  echo "📊 图表产出 (4张/篇)"
  echo "  K线图 | 板块热力图 | 资金流向图 | 涨跌分布图"
  echo ""
  echo "🕐 自动化时间线"
  echo "  15:30  数据采集"
  echo "  16:00  图表生成 + AI写作"
  echo "  17:00  微信草稿箱同步（含图表上传）"
  echo "  18:00  微信推送通知"
  echo ""
  echo "查看完整文档: cat $DOMAIN_DIR/README.md"
else
  echo "❌ 部分组件未就绪，请检查上述标记项"
fi

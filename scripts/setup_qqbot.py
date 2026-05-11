#!/usr/bin/env python3
"""QQ Bot QR 扫码注册 — 独立运行，不依赖 gateway。

用法: python3 setup_qqbot.py
→ 显示 QR 码 → 用户用 QQ 扫码 → 输出 app_id + client_secret
→ 写入 ~/.hermes/.env 供 gateway 使用
"""

import sys, os, time, json
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent/gateway"))

from pathlib import Path
from gateway.platforms.qqbot.onboard import qr_register, BindStatus

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
ENV_FILE = HERMES_HOME / ".env"

def main():
    print("🔧 QQ Bot 扫码注册")
    print("=" * 50)
    print("请准备用手机 QQ 扫描即将显示的二维码")
    print("超时时间: 10分钟")
    print()
    
    # 确保 qrcode 可用
    try:
        import qrcode
    except ImportError:
        print("⚠️  qrcode 未安装，将只显示 URL。安装: pip install qrcode")
    
    result = qr_register(timeout_seconds=600)
    
    if result is None:
        print("\n❌ 注册失败或超时")
        return 1
    
    app_id = result["app_id"]
    client_secret = result["client_secret"]
    user_openid = result.get("user_openid", "")
    
    print(f"\n✅ 注册成功!")
    print(f"   App ID: {app_id}")
    print(f"   Secret: {client_secret[:8]}...")
    if user_openid:
        print(f"   OpenID: {user_openid}")
    
    # 写入 .env
    env_content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    
    # 更新或添加 QQ Bot 配置
    lines = env_content.split("\n")
    new_lines = []
    updated_appid = False
    updated_secret = False
    
    for line in lines:
        if line.startswith("QQ_BOT_APP_ID="):
            new_lines.append(f"QQ_BOT_APP_ID={app_id}")
            updated_appid = True
        elif line.startswith("QQ_BOT_CLIENT_SECRET="):
            new_lines.append(f"QQ_BOT_CLIENT_SECRET={client_secret}")
            updated_secret = True
        else:
            new_lines.append(line)
    
    if not updated_appid:
        new_lines.append(f"QQ_BOT_APP_ID={app_id}")
    if not updated_secret:
        new_lines.append(f"QQ_BOT_CLIENT_SECRET={client_secret}")
    if user_openid and "QQ_BOT_USER_OPENID=" not in env_content:
        new_lines.append(f"QQ_BOT_USER_OPENID={user_openid}")
    
    ENV_FILE.write_text("\n".join(new_lines))
    print(f"\n📝 已写入 {ENV_FILE}")
    print("\n下一步: 重启 gateway 使配置生效")
    print("  hermes gateway restart")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

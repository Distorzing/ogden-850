#!/bin/bash
# Ogden 850 — 本地服务器（手机可通过局域网访问）
# 用法: bash serve.sh [port]

PORT=${1:-8080}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 获取本机局域网 IP
get_local_ip() {
  ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | head -1
}

LOCAL_IP=$(get_local_ip)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📘 Ogden 850 每日背词 — 手机访问"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🔗 手机浏览器打开:"
echo "     http://${LOCAL_IP}:${PORT}/desktop_words.html"
echo ""
echo "  📱 iOS Safari: 点击分享 → 「添加到主屏幕」"
echo "  🤖 Android Chrome: 点击菜单 → 「添加到主屏幕」"
echo ""
echo "  ⚠️  确保手机和 Mac 在同一 WiFi 网络"
echo "  ⏹  按 Ctrl+C 停止服务器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$SCRIPT_DIR"
python3 -m http.server "$PORT"

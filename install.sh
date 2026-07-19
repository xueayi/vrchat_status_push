#!/bin/bash
# VRChat Status Webhook Push — 自适应安装/卸载/查看 systemd 服务
# 用法:
#   sudo bash install.sh           安装并启动
#   sudo bash install.sh uninstall  卸载
#   sudo bash install.sh status     查看状态
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3 2>/dev/null || which python)"
SERVICE_NAME="vrchat-status-push"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

install_service() {
    echo "项目目录: $PROJECT_DIR"
    echo "Python:    $PYTHON"

    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=VRChat Status Webhook Push
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$PYTHON $PROJECT_DIR/main.py -c $PROJECT_DIR/config.json -s $PROJECT_DIR/data/state.json
WorkingDirectory=$PROJECT_DIR
Restart=always
RestartSec=30
User=${SUDO_USER:-$USER}

[Install]
WantedBy=multi-user.target
EOF

    echo "已安装: $SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$SERVICE_NAME"
    echo "服务已启动"
    sudo systemctl status "$SERVICE_NAME" --no-pager
}

uninstall_service() {
    if [ ! -f "$SERVICE_FILE" ]; then
        echo "未找到服务文件: $SERVICE_FILE"
        exit 1
    fi
    echo "正在停止并禁用 $SERVICE_NAME ..."
    sudo systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "$SERVICE_NAME 已卸载"
}

show_status() {
    if [ ! -f "$SERVICE_FILE" ]; then
        echo "$SERVICE_NAME 未安装"
    else
        sudo systemctl status "$SERVICE_NAME" --no-pager 2>/dev/null || true
    fi
    echo ""
    echo "--- 程序状态 ---"
    cd "$PROJECT_DIR"
    $PYTHON main.py --status 2>/dev/null || echo "无法获取状态（程序可能未运行或依赖缺失）"
}

case "${1:-}" in
    uninstall) uninstall_service ;;
    status)    show_status ;;
    *)         install_service ;;
esac

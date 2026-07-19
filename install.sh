#!/bin/bash
# VRChat Status Webhook Push — 自适应安装 systemd 服务
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3 2>/dev/null || which python)"
SERVICE_NAME="vrchat-status-push"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "项目目录: $PROJECT_DIR"
echo "Python:    $PYTHON"

# 生成 service 文件
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
User=$USER

[Install]
WantedBy=multi-user.target
EOF

echo "已安装: $SERVICE_FILE"

# 重载并启用
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo "服务已启动"
systemctl status "$SERVICE_NAME" --no-pager

#!/usr/bin/env bash
# CampusEvent 一键部署脚本（Linux 云服务器）
# 用法：bash deploy/deploy.sh [端口，默认 8000]
set -euo pipefail

PORT="${1:-8000}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

echo "[1/5] 创建虚拟环境"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "[2/5] 运行自动化测试（23 条）"
.venv/bin/python -m pytest -q

echo "[3/5] 生成会话密钥"
if [ ! -f .env ]; then
  {
    echo "CAMPUS_EVENT_SECRET=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')"
    echo "CAMPUS_EVENT_ADMIN_PASSWORD=admin123"
  } > .env
  echo "已写入 .env（请勿提交到 Git）"
fi

echo "[4/5] 后台启动 gunicorn 于 0.0.0.0:${PORT}"
set -a; . ./.env; set +a
pkill -f "gunicorn .*run:app" 2>/dev/null || true
nohup .venv/bin/gunicorn -w 2 -b "0.0.0.0:${PORT}" run:app \
  --access-logfile /var/log/campus-event-access.log \
  --error-logfile /var/log/campus-event-error.log \
  --daemon
sleep 3

echo "[5/5] 自检"
curl -s -o /dev/null -w "GET /login -> %{http_code}\n" "http://127.0.0.1:${PORT}/login"
echo "本机访问：http://127.0.0.1:${PORT}"
echo "外网访问需在云服务器安全组放行 ${PORT} 端口，并使用公网 IP 访问。"

#!/bin/bash
# 正式机首次上线（在 47 上以 root 执行）
# 前置：/tmp/backpack-quant.tgz 已上传
set -euo pipefail

APP_DIR="/opt/backpack-quant"
PKG="/tmp/backpack-quant.tgz"
OLD_ENV="/opt/trading/ending/backpack_quant_trading/.env"
NGINX_HTTPS="/etc/nginx/conf.d/https_proxy.conf"

if [ ! -f "${PKG}" ]; then
  echo "缺少 ${PKG}" >&2
  exit 1
fi

echo "==> 解压到 ${APP_DIR}"
mkdir -p "${APP_DIR}"
tar -xzf "${PKG}" -C "${APP_DIR}"
rm -f "${PKG}"
cd "${APP_DIR}"
chmod +x deploy/*.sh 2>/dev/null || true

echo "==> 确保 swap + Docker"
bash deploy/ensure-swap.sh
bash deploy/install-docker.sh

echo "==> 准备 .env（从旧栈复制，不覆盖已有）"
if [ ! -f .env ]; then
  if [ -f "${OLD_ENV}" ]; then
    cp -a "${OLD_ENV}" .env
    echo "已从旧栈复制 .env"
  elif [ -f deploy/env.prod.example ]; then
    cp deploy/env.prod.example .env
  else
    cp deploy/env.example .env
  fi
fi

# 外部 MySQL + 宿主机代理（幂等）
if grep -qE '^DB_HOST=' .env; then
  sed -i 's/^DB_HOST=.*/DB_HOST=host.docker.internal/' .env
else
  echo 'DB_HOST=host.docker.internal' >> .env
fi
if grep -qE '^HTTP_PROXY=' .env; then
  sed -i 's|^HTTP_PROXY=.*|HTTP_PROXY=http://host.docker.internal:7891|' .env
else
  echo 'HTTP_PROXY=http://host.docker.internal:7891' >> .env
fi
if grep -qE '^HTTPS_PROXY=' .env; then
  sed -i 's|^HTTPS_PROXY=.*|HTTPS_PROXY=http://host.docker.internal:7891|' .env
else
  echo 'HTTPS_PROXY=http://host.docker.internal:7891' >> .env
fi
if ! grep -qE '^NO_PROXY=' .env; then
  echo 'NO_PROXY=localhost,127.0.0.1,api,webhook,dingtalk-agent,host.docker.internal' >> .env
fi
grep -E '^(DB_HOST|HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' .env | sed 's/=.*/=***/'

echo "==> 停止旧 Python 栈（8100/8005），保留 nginx/mihomo/mysql"
for pid in $(ss -tlnp | grep -E ':8100|:8005' | grep -oP 'pid=\K[0-9]+' | sort -u); do
  cmd=$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)
  echo "停止 pid=${pid} ${cmd}"
  kill "${pid}" 2>/dev/null || true
done
sleep 2
# 仍占则强杀
for p in 8100 8005; do
  for pid in $(ss -tlnp "sport = :${p}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do
    echo "SIGKILL pid=${pid} :${p}"
    kill -9 "${pid}" 2>/dev/null || true
  done
done

echo "==> 备份并调整 Nginx：/ → 8100"
cp -a "${NGINX_HTTPS}" "${NGINX_HTTPS}.bak.$(date +%Y%m%d%H%M%S)"
# 仅改 location / 的 proxy_pass（保留 /service /webhook /api）
python3 - <<'PY'
from pathlib import Path
p = Path("/etc/nginx/conf.d/https_proxy.conf")
text = p.read_text(encoding="utf-8")
old = """    location / {
        proxy_pass http://0.0.0.0:8050;
    }"""
new = """    location / {
        proxy_pass http://127.0.0.1:8100/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }"""
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("patched location / -> 8100")
elif "proxy_pass http://127.0.0.1:8100/;" in text or "proxy_pass http://127.0.0.1:8100;" in text:
    print("location / already points to 8100")
else:
    print("WARNING: could not find exact location / block; please merge manually")
    print(text)
PY
nginx -t
systemctl reload nginx
echo "mulong.conf 未改动"

echo "==> docker compose 部署（外部 MySQL）"
export SKIP_MYSQL=1
export DEPLOY_ENV=prod
bash deploy/deploy.sh

echo "==> 验收"
bash deploy/verify-prod.sh || true

echo "==> first-prod-up 完成"

#!/bin/bash
# 杀掉慢构建，经 172.17.0.1:7891 代理重构建并启动
set -euo pipefail
cd /opt/backpack-quant

echo "==> 停止卡住的构建/部署"
pkill -f 'continue-prod-deploy.sh' 2>/dev/null || true
pkill -f 'bash deploy/deploy.sh' 2>/dev/null || true
# 取消 buildkit 会话（尽量）
docker ps -aq | xargs -r docker rm -f 2>/dev/null || true
# 不杀 dockerd；只清 dangling build
kill 2295906 2295585 2295574 2>/dev/null || true
sleep 2

echo "==> 确认 mihomo"
ss -tlnp | grep 7891 || { echo "mihomo 未监听"; exit 1; }

echo "==> .env：构建与容器都走 172.17.0.1:7891"
sed -i 's|^DB_HOST=.*|DB_HOST=host.docker.internal|' .env
# 构建时 compose 会读这些；172.17.0.1 对 build 容器可达（mihomo 已 *:7891）
sed -i 's|^HTTP_PROXY=.*|HTTP_PROXY=http://172.17.0.1:7891|' .env
sed -i 's|^HTTPS_PROXY=.*|HTTPS_PROXY=http://172.17.0.1:7891|' .env
sed -i 's|^ALL_PROXY=.*|ALL_PROXY=|' .env || true
grep -q '^CONTAINER_HTTP_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTP_PROXY=.*|CONTAINER_HTTP_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTP_PROXY=http://172.17.0.1:7891' >> .env
grep -q '^CONTAINER_HTTPS_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTPS_PROXY=.*|CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891' >> .env
grep -E 'PROXY|DB_HOST' .env | sed 's/=.*/=***/'

# 临时改 deploy.sh：不要 unset 代理（本次需要代理加速 apt）
# 直接手动 build + up
export SKIP_MYSQL=1
export COMPOSE_PROFILES=""
export HTTP_PROXY=http://172.17.0.1:7891
export HTTPS_PROXY=http://172.17.0.1:7891
export NO_PROXY=localhost,127.0.0.1,mysql,api,webhook,dingtalk-agent,host.docker.internal,172.17.0.1,deb.debian.org

echo "==> docker compose build（经代理）"
docker compose build --pull

echo "==> 启动 api"
docker compose up -d --remove-orphans api

echo "==> 等 health"
ok=0
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    curl -s http://127.0.0.1:8100/api/health; echo
    ok=1
    break
  fi
  state=$(docker inspect -f '{{.State.Status}}' backpack-api 2>/dev/null || echo missing)
  echo "wait api ($i/40) state=$state"
  if [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
    docker compose logs --tail=80 api || true
    exit 1
  fi
  sleep 5
done
if [ "$ok" != "1" ]; then
  docker compose logs --tail=120 api || true
  exit 1
fi

docker compose up -d webhook dingtalk-agent
docker compose ps -a
bash deploy/verify-prod.sh || true
echo "==> done"

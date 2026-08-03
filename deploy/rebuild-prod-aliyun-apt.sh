#!/bin/bash
set -euo pipefail
cd /opt/backpack-quant

echo "==> 停掉卡住的构建"
pkill -f 'rebuild-prod-with-proxy.sh' 2>/dev/null || true
pkill -f 'continue-prod-deploy.sh' 2>/dev/null || true
# 杀掉 buildkit 里的 apt
ps aux | grep -E 'apt-get|runc.*buildkit' | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null || true
sleep 2

echo "==> 确认 Dockerfile 已含阿里云 apt 源"
grep -n aliyun Dockerfile | head -5

export SKIP_MYSQL=1
# 构建可不走代理（阿里云源）；容器运行仍要代理访问币安
# 清空会污染 build 的 HTTP_PROXY，避免解析失败；容器用 CONTAINER_* 
sed -i 's|^HTTP_PROXY=.*|HTTP_PROXY=|' .env
sed -i 's|^HTTPS_PROXY=.*|HTTPS_PROXY=|' .env
grep -q '^CONTAINER_HTTP_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTP_PROXY=.*|CONTAINER_HTTP_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTP_PROXY=http://172.17.0.1:7891' >> .env
grep -q '^CONTAINER_HTTPS_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTPS_PROXY=.*|CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891' >> .env

echo "==> build（无宿主机代理 env，走阿里云 debian）"
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  docker compose build

echo "==> up"
export SKIP_MYSQL=1
bash deploy/deploy.sh
bash deploy/verify-prod.sh || true

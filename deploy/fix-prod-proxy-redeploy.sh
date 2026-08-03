#!/bin/bash
set -euo pipefail

echo "==> sync files already expected under /opt/backpack-quant"

echo "==> enable mihomo allow-lan"
cfg=/root/.config/mihomo/config.yaml
cp -a "$cfg" "$cfg.bak.$(date +%Y%m%d%H%M%S)"
sed -i 's/^allow-lan:.*/allow-lan: true/' "$cfg"

# restart mihomo
pkill -x mihomo || true
sleep 1
BIN=""
for b in /usr/local/bin/mihomo /usr/bin/mihomo /root/mihomo/mihomo; do
  if [ -x "$b" ]; then BIN="$b"; break; fi
done
if [ -z "$BIN" ]; then
  BIN=$(command -v mihomo || true)
fi
if [ -z "$BIN" ]; then
  echo "找不到 mihomo 二进制" >&2
  exit 1
fi
nohup "$BIN" -d /root/.config/mihomo >/var/log/mihomo.log 2>&1 &
sleep 2
ss -tlnp | grep 7891 || { echo "mihomo 未监听 7891"; tail -30 /var/log/mihomo.log; exit 1; }
grep -E 'allow-lan|mixed-port|bind' "$cfg" | head -5

echo "==> fix .env proxy"
cd /opt/backpack-quant
sed -i 's|^HTTP_PROXY=.*|HTTP_PROXY=|' .env
sed -i 's|^HTTPS_PROXY=.*|HTTPS_PROXY=|' .env
sed -i 's|^ALL_PROXY=.*|ALL_PROXY=|' .env || true
grep -q '^CONTAINER_HTTP_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTP_PROXY=.*|CONTAINER_HTTP_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTP_PROXY=http://172.17.0.1:7891' >> .env
grep -q '^CONTAINER_HTTPS_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTPS_PROXY=.*|CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891' >> .env
# 确保 DB 指向宿主机
sed -i 's|^DB_HOST=.*|DB_HOST=host.docker.internal|' .env
grep -E 'PROXY|DB_HOST' .env | sed 's/=.*/=***/'

echo "==> deploy"
chmod +x deploy/deploy.sh
export SKIP_MYSQL=1
bash deploy/deploy.sh
bash deploy/verify-prod.sh || true

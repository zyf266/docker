#!/bin/bash
set -euo pipefail
cd /opt/backpack-quant

echo "==> fix .env for external DB + container proxy"
sed -i 's|^DB_HOST=.*|DB_HOST=host.docker.internal|' .env
sed -i 's|^HTTP_PROXY=.*|HTTP_PROXY=|' .env
sed -i 's|^HTTPS_PROXY=.*|HTTPS_PROXY=|' .env
sed -i 's|^ALL_PROXY=.*|ALL_PROXY=|' .env || true
grep -q '^CONTAINER_HTTP_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTP_PROXY=.*|CONTAINER_HTTP_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTP_PROXY=http://172.17.0.1:7891' >> .env
grep -q '^CONTAINER_HTTPS_PROXY=' .env \
  && sed -i 's|^CONTAINER_HTTPS_PROXY=.*|CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891|' .env \
  || echo 'CONTAINER_HTTPS_PROXY=http://172.17.0.1:7891' >> .env
grep -E 'PROXY|DB_HOST' .env | sed 's/=.*/=***/'

# persist mihomo with correct binary (optional, non-fatal)
if [ -x /root/.local/bin/mihomo ]; then
  cat >/etc/systemd/system/mihomo.service <<'EOF'
[Unit]
Description=Mihomo Proxy Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/root/.local/bin/mihomo -d /root/.config/mihomo
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  # don't restart if already listening
  if ss -tlnp | grep -q ':7891'; then
    echo "mihomo already listening; systemd unit updated only"
  else
    systemctl restart mihomo
  fi
  systemctl enable mihomo >/dev/null 2>&1 || true
fi

echo "==> ports before deploy"
ss -tlnp | grep -E ':8100|:8005|:7891' || true

export SKIP_MYSQL=1
bash deploy/deploy.sh
bash deploy/verify-prod.sh || true

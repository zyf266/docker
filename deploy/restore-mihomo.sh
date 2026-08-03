#!/bin/bash
set -euo pipefail

CFG=/root/.config/mihomo/config.yaml
echo "==> restore config from backup"
latest=$(ls -t /root/.config/mihomo/config.yaml.bak.* 2>/dev/null | head -1 || true)
if [ -n "${latest}" ]; then
  cp -a "${latest}" "${CFG}"
  echo "restored from ${latest}"
fi

# only flip allow-lan; do not change proxy types
sed -i 's/^allow-lan:.*/allow-lan: true/' "${CFG}"
grep -nE '^(allow-lan|mixed-port|bind-address):' "${CFG}" | head -10

echo "==> locate mihomo binary"
BIN=""
for b in /usr/local/bin/mihomo /usr/bin/mihomo /root/mihomo/mihomo /opt/mihomo/mihomo; do
  if [ -x "$b" ]; then
    echo "found $b version: $($b -v 2>&1 | head -1 || true)"
    BIN="$b"
  fi
done
# also search
while IFS= read -r f; do
  echo "found $f"
  BIN="$f"
done < <(find /root /usr/local /opt -name 'mihomo' -type f 2>/dev/null | head -10)

# history hints
echo "==> history"
grep -n mihomo /root/.bash_history 2>/dev/null | tail -30 || true
systemctl list-unit-files 2>/dev/null | grep -iE 'mihomo|clash' || true
ls -la /etc/systemd/system/*mihomo* /etc/systemd/system/*clash* 2>/dev/null || true

# Prefer binary that accepts current config
pick=""
for b in /usr/local/bin/mihomo /usr/bin/mihomo /root/mihomo/mihomo $BIN; do
  [ -x "$b" ] || continue
  if "$b" -t -d /root/.config/mihomo >/tmp/mihomo-test.out 2>&1; then
    echo "OK test: $b"
    pick="$b"
    break
  else
    echo "FAIL test: $b"
    tail -5 /tmp/mihomo-test.out || true
  fi
done

if [ -z "$pick" ]; then
  echo "无可用 mihomo，尝试原配置 allow-lan false 启动旧能力"
  sed -i 's/^allow-lan:.*/allow-lan: false/' "${CFG}"
  for b in /usr/local/bin/mihomo /usr/bin/mihomo /root/mihomo/mihomo; do
    [ -x "$b" ] || continue
    if "$b" -t -d /root/.config/mihomo >/tmp/mihomo-test.out 2>&1; then
      pick="$b"
      break
    fi
  done
fi

if [ -z "$pick" ]; then
  echo "仍然无法启动 mihomo" >&2
  exit 1
fi

pkill -x mihomo 2>/dev/null || true
sleep 1
nohup "$pick" -d /root/.config/mihomo >/var/log/mihomo.log 2>&1 &
sleep 3
ss -tlnp | grep 7891
echo "mihomo started with $pick"

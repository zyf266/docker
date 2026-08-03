#!/bin/bash
set -euo pipefail

echo "=== find openclaw unit / supervisor ==="
systemctl list-unit-files --all 2>/dev/null | grep -i openclaw || true
systemctl list-units --all 2>/dev/null | grep -i openclaw || true
ls /etc/systemd/system/*openclaw* 2>/dev/null || true
ls /lib/systemd/system/*openclaw* 2>/dev/null || true
ls /etc/supervisor/conf.d/*openclaw* 2>/dev/null || true
crontab -l 2>/dev/null || true
ls /etc/cron.* 2>/dev/null | head
# pm2 / docker
command -v pm2 >/dev/null && pm2 list || true
docker ps -a --format '{{.Names}} {{.Image}}' | grep -i claw || true

echo "=== parent of openclaw ==="
pgrep -a openclaw-gateway || true
for pid in $(pgrep -f '/openclaw-gateway|openclaw-gateway$' || true); do
  echo "PID=$pid PPID=$(awk '/PPid/ {print $2}' /proc/$pid/status 2>/dev/null)"
  tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null; echo
  ls -l /proc/$pid/exe 2>/dev/null || true
done

echo "=== disable & mask ==="
systemctl stop openclaw-gateway 2>/dev/null || true
systemctl disable openclaw-gateway 2>/dev/null || true
systemctl mask openclaw-gateway 2>/dev/null || true
systemctl stop openclaw 2>/dev/null || true
systemctl disable openclaw 2>/dev/null || true
systemctl mask openclaw 2>/dev/null || true

# kill by exact binary name
pkill -9 -f 'openclaw-gateway' || true
sleep 2
if pgrep -f 'openclaw-gateway' >/dev/null; then
  echo "FAILED to kill openclaw"
  pgrep -af openclaw
  exit 1
fi
echo "openclaw-gateway stopped"

# prevent respawn for a bit: rename binary if found
BIN=$(command -v openclaw-gateway || true)
if [ -n "${BIN}" ] && [ -x "$BIN" ]; then
  echo "found bin $BIN"
fi
# common install path
for p in /usr/local/bin/openclaw-gateway /root/.npm-global/bin/openclaw /usr/bin/openclaw; do
  if [ -e "$p" ]; then echo "path $p"; fi
done
find /root /usr/local /opt -name 'openclaw*' -type f 2>/dev/null | head -30

echo "=== restart our stream bot ==="
docker restart backpack-dingtalk-agent
sleep 15
docker logs backpack-dingtalk-agent --tail 12 2>&1
pgrep -af 'openclaw-gateway' || echo "OK: no openclaw-gateway"
pgrep -af 'dingtalk_score_bot' || true

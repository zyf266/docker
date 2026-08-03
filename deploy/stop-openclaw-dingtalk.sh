#!/bin/bash
set -euo pipefail
echo "=== openclaw env (ding*) ==="
tr '\0' '\n' < /proc/2723169/environ 2>/dev/null | grep -iE 'DING|SCORE|BOT|CLIENT' || true
echo "=== openclaw cwd ==="
ls -la /proc/2723169/cwd 2>/dev/null || true
echo "=== stop openclaw-gateway to free DingTalk Stream ==="
# Prefer systemd if present
if systemctl list-unit-files 2>/dev/null | grep -qi openclaw; then
  systemctl stop openclaw-gateway 2>/dev/null || systemctl stop openclaw 2>/dev/null || true
fi
kill -TERM 2723169 2>/dev/null || true
sleep 2
if kill -0 2723169 2>/dev/null; then
  echo "still alive, SIGKILL"
  kill -KILL 2723169 2>/dev/null || true
fi
sleep 1
ps aux | grep -E 'openclaw|dingtalk_score' | grep -v grep || echo "openclaw gone"
echo "=== restart dingtalk-agent for exclusive Stream ==="
docker restart backpack-dingtalk-agent
sleep 12
docker logs backpack-dingtalk-agent --tail 15 2>&1

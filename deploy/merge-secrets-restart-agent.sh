#!/bin/bash
set -euo pipefail
cd /opt/backpack-quant

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  key="${line%%=*}"
  val="${line#*=}"
  [ -z "$key" ] && continue
  if grep -qE "^${key}=" .env; then
    # escape sed specials minimally
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
done < .env.secrets

echo "merged:"
grep -E '^(ENV_SECRETS_PASSPHRASE|DINGTALK_SCORE_BOT_CLIENT_SECRET)=' .env | sed 's/=.*/=<set>/'

docker compose up -d --force-recreate dingtalk-agent
sleep 8
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker logs backpack-dingtalk-agent --tail 20 2>&1 | head -30

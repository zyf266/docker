#!/bin/bash
set -euo pipefail
cd /opt/backpack-quant

echo "==> ensure compose uses DB_HOST from .env"
grep -n 'DB_HOST' docker-compose.yml | head -10

echo "==> recreate api with correct env (no deps)"
# export from .env for compose interpolation
set -a
# shellcheck disable=SC1091
source .env
set +a
echo "compose will see DB_HOST=${DB_HOST}"

docker compose up -d --force-recreate --no-deps api
sleep 5
echo "container DB_HOST=$(docker exec backpack-api printenv DB_HOST)"

echo "==> wait health"
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    echo HEALTH_OK
    curl -sf http://127.0.0.1:8100/api/health; echo
    exit 0
  fi
  st=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' backpack-api 2>/dev/null || echo missing)
  echo "wait $i health=$st"
  if [ "$i" -eq 5 ] || [ "$i" -eq 15 ]; then
    docker logs backpack-api --tail 8 2>&1 | tail -8
  fi
  sleep 3
done
echo HEALTH_FAIL
docker logs backpack-api --tail 40
exit 1

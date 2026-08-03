#!/bin/bash
set -e
cd /opt/backpack-quant
echo "== .env DB =="
grep -E '^(DB_HOST|DB_PORT|DB_USER|SKIP_MYSQL)=' .env | sed 's/PASSWORD=.*/PASSWORD=***/'
echo "== container DB_HOST =="
docker exec backpack-api printenv DB_HOST || echo no_container_env
echo "== compose files =="
ls -l docker-compose*.yml
grep -n 'DB_HOST\|extra_hosts\|host.docker\|env_file' docker-compose.yml | head -40
if [ -f docker-compose.prod.yml ]; then
  grep -n 'DB_HOST\|extra_hosts\|host.docker\|env_file' docker-compose.prod.yml | head -40
fi
echo "== mysql host port =="
ss -lntp | grep 3306 || true
mysqladmin ping -h127.0.0.1 --silent && echo mysql_local_ok || echo mysql_local_fail

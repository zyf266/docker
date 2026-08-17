#!/bin/bash
# 服务器端：构建并重启（代码已由 Actions SCP 同步，不再 git pull）
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
cd "${APP_DIR}"

_read_env() {
  local key="$1"
  local def="${2:-}"
  if [ ! -f .env ]; then
    echo "${def}"
    return
  fi
  local val
  val=$(grep -E "^${key}=" .env | tail -n1 | cut -d= -f2- | tr -d '\r' | sed 's/^["'\'']//;s/["'\'']$//' || true)
  if [ -z "${val}" ]; then
    echo "${def}"
  else
    echo "${val}"
  fi
}

if [ -x deploy/ensure-swap.sh ]; then
  echo "==> 确保 swap"
  bash deploy/ensure-swap.sh
fi

DB_HOST="$(_read_env DB_HOST mysql)"
SKIP_MYSQL="${SKIP_MYSQL:-0}"
USE_LOCAL_MYSQL=0
if [ "${SKIP_MYSQL}" = "1" ]; then
  USE_LOCAL_MYSQL=0
elif [ "${DB_HOST}" = "mysql" ] || [ -z "${DB_HOST}" ]; then
  USE_LOCAL_MYSQL=1
fi

COMPOSE=(docker compose)
if [ "${USE_LOCAL_MYSQL}" = "1" ]; then
  case ",${COMPOSE_PROFILES:-}," in
    *,local-mysql,*) ;;
    *) export COMPOSE_PROFILES="${COMPOSE_PROFILES:+$COMPOSE_PROFILES,}local-mysql" ;;
  esac
  echo "==> 使用 compose MySQL (profile=local-mysql, DB_HOST=${DB_HOST})"
else
  echo "==> 使用外部 MySQL (DB_HOST=${DB_HOST})，跳过 compose mysql"
  # 去掉 local-mysql，避免误启
  if [ -n "${COMPOSE_PROFILES:-}" ]; then
    COMPOSE_PROFILES=$(echo "${COMPOSE_PROFILES}" | tr ',' '\n' | grep -vx 'local-mysql' | paste -sd, - || true)
    export COMPOSE_PROFILES
  fi
fi

# 前端必须预构建：小内存 ECS 上跑 npm 会 OOM（npm Exit handler never called / vite not found）
if [ ! -f backpack_quant_trading/frontend/dist/index.html ]; then
  echo "ERROR: 缺少 backpack_quant_trading/frontend/dist/index.html" >&2
  echo "正式/测试部署应由 GitHub Actions 先执行 deploy/build-frontend.sh 再打包。" >&2
  echo "本地可先: bash deploy/build-frontend.sh" >&2
  exit 1
fi
echo "==> 已检测到预构建前端 dist"

echo "==> 构建镜像（清除宿主机代理，避免 BuildKit 解析 host.docker.internal 失败）..."
# compose 会读 .env 里的 HTTP(S)_PROXY 并传给 build；构建应走 registry-mirrors / 本机直连
# 构建期不再跑 Node，内存压力显著下降
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  -u FTP_PROXY -u ftp_proxy \
  "${COMPOSE[@]}" build --pull

if [ "${USE_LOCAL_MYSQL}" = "1" ]; then
  echo "==> 先启动 MySQL（小内存机器需等 healthy 再起 api）..."
  "${COMPOSE[@]}" --profile local-mysql up -d --remove-orphans mysql

  mysql_ok=0
  i=1
  while [ "${i}" -le 30 ]; do
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' backpack-mysql 2>/dev/null || echo missing)
    if [ "${health}" = "healthy" ]; then
      mysql_ok=1
      break
    fi
    state=$(docker inspect -f '{{.State.Status}}' backpack-mysql 2>/dev/null || echo missing)
    if [ "${state}" = "exited" ] || [ "${state}" = "dead" ] || [ "${state}" = "missing" ]; then
      echo "MySQL 容器状态异常: ${state}" >&2
      "${COMPOSE[@]}" logs --tail=80 mysql || true
      free -h || true
      exit 1
    fi
    echo "等待 MySQL... (${i}/30) state=${state} health=${health}"
    sleep 3
    i=$((i + 1))
  done

  if [ "${mysql_ok}" != "1" ]; then
    echo "MySQL 健康检查失败（常见原因：内存不足 / OOM）" >&2
    "${COMPOSE[@]}" logs --tail=80 mysql || true
    free -h || true
    dmesg -T 2>/dev/null | grep -i oom | tail -3 || true
    exit 1
  fi
fi

echo "==> 启动 api..."
if [ "${USE_LOCAL_MYSQL}" = "1" ]; then
  "${COMPOSE[@]}" --profile local-mysql up -d --remove-orphans api
else
  "${COMPOSE[@]}" up -d --remove-orphans api
fi

echo "==> 等待 API 健康..."
ok=0
i=1
while [ "${i}" -le 40 ]; do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    curl -s http://127.0.0.1:8100/api/health
    echo ""
    ok=1
    break
  fi
  state=$(docker inspect -f '{{.State.Status}}' backpack-api 2>/dev/null || echo missing)
  health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' backpack-api 2>/dev/null || echo none)
  if [ "${state}" = "exited" ] || [ "${state}" = "dead" ] || [ "${state}" = "missing" ]; then
    echo "API 容器状态异常: ${state}" >&2
    "${COMPOSE[@]}" logs --tail=120 api || true
    exit 1
  fi
  echo "等待 API... (${i}/40) state=${state} health=${health}"
  sleep 5
  i=$((i + 1))
done

if [ "${ok}" != "1" ]; then
  echo "API 健康检查失败：" >&2
  "${COMPOSE[@]}" logs --tail=120 api || true
  "${COMPOSE[@]}" ps -a || true
  exit 1
fi

echo "==> 启动 webhook..."
"${COMPOSE[@]}" up -d webhook

echo "==> 启动 dingtalk-agent（Stream 多 Agent / 旧评分同进程）..."
"${COMPOSE[@]}" up -d dingtalk-agent

# 代理自检（不阻断部署）
HTTPS_PROXY_VAL="$(_read_env HTTPS_PROXY)"
if [ -n "${HTTPS_PROXY_VAL}" ]; then
  echo "==> 代理自检 (HTTPS_PROXY=${HTTPS_PROXY_VAL})..."
  if docker exec backpack-api curl -sf --max-time 15 -x "${HTTPS_PROXY_VAL}" \
    https://fapi.binance.com/fapi/v1/ping >/dev/null 2>&1; then
    echo "代理可达 Binance fapi"
  else
    echo "警告: 经代理 ping Binance 失败（不阻断部署，请检查宿主机 mihomo :7891）" >&2
  fi
fi

echo "==> 清理旧镜像..."
docker image prune -f

echo "==> 服务状态:"
"${COMPOSE[@]}" ps -a

echo "==> 部署完成"

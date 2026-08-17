#!/usr/bin/env bash
# 预构建前端 dist（供 Docker 镜像 COPY，避免 ECS 内 npm OOM）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FE="${ROOT}/backpack_quant_trading/frontend"
cd "${FE}"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: 需要 Node.js/npm 才能构建前端" >&2
  exit 1
fi

echo "==> frontend: npm install (registry=${NPM_CONFIG_REGISTRY:-default})"
export NODE_ENV=development
export NPM_CONFIG_PRODUCTION=false
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=2048}"

if [ -f package-lock.json ]; then
  npm ci --ignore-scripts || npm install --ignore-scripts --no-audit --no-fund
else
  npm install --ignore-scripts --no-audit --no-fund
fi

test -x node_modules/.bin/vite || test -f node_modules/vite/bin/vite.js

echo "==> frontend: npm run build"
npm run build
test -f dist/index.html
echo "==> frontend dist OK: ${FE}/dist/index.html"

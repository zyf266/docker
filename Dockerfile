# ── Stage 1: 构建前端 ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build
# 构建期必须拿到 vite；CI/生产常默认 NODE_ENV=production 会跳过 devDependencies
ENV NODE_ENV=development
# 避免宿主机/compose 传入的 npm 生产模式污染
ENV NPM_CONFIG_PRODUCTION=false

COPY backpack_quant_trading/frontend/package.json backpack_quant_trading/frontend/package-lock.json* ./
RUN (npm ci --include=dev --ignore-scripts || npm install --include=dev --ignore-scripts) \
  && test -x node_modules/.bin/vite

COPY backpack_quant_trading/frontend/ ./
RUN npm run build \
  && test -f dist/index.html

# ── Stage 2: Python 运行环境 ─────────────────────────────────
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TRADING_SERVER=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 国内构建：Debian 官方源极慢，改阿里云镜像
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's/deb.debian.org/mirrors.aliyun.com/g; s/security.debian.org/mirrors.aliyun.com/g' \
        /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i 's/deb.debian.org/mirrors.aliyun.com/g; s/security.debian.org/mirrors.aliyun.com/g' \
        /etc/apt/sources.list; \
    fi; \
    apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libffi-dev default-libmysqlclient-dev pkg-config curl tzdata \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo Asia/Shanghai > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY backpack_quant_trading/requirements.txt /app/backpack_quant_trading/requirements.txt
# 国内 ECS 构建时走清华 PyPI 源，更稳
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r /app/backpack_quant_trading/requirements.txt

COPY backpack_quant_trading/ /app/backpack_quant_trading/
COPY --from=frontend-builder /build/dist /app/backpack_quant_trading/frontend/dist

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8100 8005

ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]

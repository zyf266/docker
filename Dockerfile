# ── Stage 1: 构建前端 ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY backpack_quant_trading/frontend/package.json backpack_quant_trading/frontend/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install

COPY backpack_quant_trading/frontend/ ./
RUN npm run build

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

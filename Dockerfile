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
    TRADING_SERVER=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libffi-dev default-libmysqlclient-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*

COPY backpack_quant_trading/requirements.txt /app/backpack_quant_trading/requirements.txt
RUN pip install --no-cache-dir -r /app/backpack_quant_trading/requirements.txt

COPY backpack_quant_trading/ /app/backpack_quant_trading/
COPY --from=frontend-builder /build/dist /app/backpack_quant_trading/frontend/dist

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8100 8005

ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]

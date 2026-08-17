# 正式/测试机 Docker 构建：不再在 ECS 上跑 npm（小内存易 OOM → Exit handler never called）。
# 前端必须由 GitHub Actions（或本地）预先产出 backpack_quant_trading/frontend/dist。
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

# 强制要求预构建前端，避免静默带上空 dist
RUN test -f /app/backpack_quant_trading/frontend/dist/index.html \
    || (echo "ERROR: 缺少 frontend/dist/index.html。请先在 CI/本地执行 deploy/build-frontend.sh" >&2; exit 1)

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8100 8005

ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]

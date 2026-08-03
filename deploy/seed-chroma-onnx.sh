#!/usr/bin/env bash
# 把本机下好的 onnx.tar.gz 铺到服务器缓存，避免容器内从 AWS 慢速下载。
# 用法:
#   1) 浏览器打开下载: https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz
#   2) bash deploy/seed-chroma-onnx.sh /path/to/onnx.tar.gz
set -euo pipefail
SRC="${1:-}"
if [ -z "${SRC}" ] || [ ! -f "${SRC}" ]; then
  echo "用法: $0 /path/to/onnx.tar.gz" >&2
  exit 1
fi
DEST_HOST="${DEST_HOST:-/opt/backpack-quant/deploy/chroma_onnx/all-MiniLM-L6-v2}"
mkdir -p "${DEST_HOST}"
cp -f "${SRC}" "${DEST_HOST}/onnx.tar.gz"
# 解压供 chroma 识别 model.onnx
tar -xzf "${DEST_HOST}/onnx.tar.gz" -C "${DEST_HOST}"
echo "已写入 ${DEST_HOST}"
ls -lah "${DEST_HOST}" | head
echo "然后: docker compose up -d --force-recreate dingtalk-agent"
echo "可选: CHROMA_EMBEDDING_MODE=onnx"

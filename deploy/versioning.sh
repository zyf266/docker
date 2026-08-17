#!/usr/bin/env bash
# 版本发布 / 回滚辅助（正式服）
# 版本号格式: YYYYMMDD-HHMMSS-<git短sha>  例: 20260817-090015-a1b2c3d
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
RELEASE_ROOT="${RELEASE_ROOT:-/opt/backpack-quant-releases}"
IMAGE_NAME="${IMAGE_NAME:-backpack-quant}"
KEEP_N="${KEEP_RELEASES:-5}"

_ts_utc() { date -u +%Y%m%d-%H%M%S; }

make_version() {
  local sha="${1:-unknown}"
  sha="$(echo "${sha}" | tr -d '\r\n' | cut -c1-7)"
  if [ -z "${sha}" ] || [ "${sha}" = "unknown" ]; then
    sha="local"
  fi
  echo "$(_ts_utc)-${sha}"
}

ensure_release_dirs() {
  mkdir -p "${RELEASE_ROOT}"
}

write_current_version() {
  local ver="$1"
  mkdir -p "${APP_DIR}"
  printf '%s\n' "${ver}" > "${APP_DIR}/VERSION"
  printf '%s\n' "${ver}" > "${APP_DIR}/backpack_quant_trading/VERSION" 2>/dev/null || true
}

record_release_meta() {
  local ver="$1"
  local sha="${2:-}"
  local mode="${3:-deploy}"
  local dir="${RELEASE_ROOT}/${ver}"
  mkdir -p "${dir}"
  cat > "${dir}/meta.json" <<EOF
{
  "version": "${ver}",
  "git_sha": "${sha}",
  "mode": "${mode}",
  "recorded_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "image": "${IMAGE_NAME}:${ver}"
}
EOF
  echo "${ver}" >> "${RELEASE_ROOT}/history.txt"
  # 去重保留顺序：history 只追加；清理时按目录处理
}

tag_image_version() {
  local ver="$1"
  if ! docker image inspect "${IMAGE_NAME}:latest" >/dev/null 2>&1; then
    echo "ERROR: 缺少 ${IMAGE_NAME}:latest，无法打版本标签" >&2
    exit 1
  fi
  docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:${ver}"
  echo "==> 已标记镜像 ${IMAGE_NAME}:${ver}"
}

list_versions() {
  echo "==> 磁盘发布包:"
  if [ -d "${RELEASE_ROOT}" ]; then
    ls -1dt "${RELEASE_ROOT}"/*/ 2>/dev/null | head -n 20 || true
  fi
  echo "==> Docker 镜像标签:"
  docker images "${IMAGE_NAME}" --format '{{.Tag}}\t{{.ID}}\t{{.CreatedSince}}' 2>/dev/null | head -n 30 || true
  echo "==> 当前 VERSION 文件:"
  if [ -f "${APP_DIR}/VERSION" ]; then
    cat "${APP_DIR}/VERSION"
  else
    echo "(无)"
  fi
}

# 保留最近 KEEP_N 个带时间戳的镜像标签 + 发布目录；不动 latest
prune_old_releases() {
  local keep="${KEEP_N}"
  echo "==> 清理旧版本（保留最近 ${keep} 个）"

  # 镜像：按 CreatedAt 倒序，跳过 latest / <none>
  mapfile -t tags < <(docker images "${IMAGE_NAME}" --format '{{.Tag}}' | grep -E '^[0-9]{8}-' || true)
  local i=0
  for t in "${tags[@]}"; do
    i=$((i + 1))
    if [ "${i}" -gt "${keep}" ]; then
      echo "  删除镜像 ${IMAGE_NAME}:${t}"
      docker rmi "${IMAGE_NAME}:${t}" >/dev/null 2>&1 || true
    fi
  done

  # 发布目录
  mapfile -t dirs < <(ls -1dt "${RELEASE_ROOT}"/*/ 2>/dev/null || true)
  i=0
  for d in "${dirs[@]}"; do
    i=$((i + 1))
    if [ "${i}" -gt "${keep}" ]; then
      echo "  删除发布目录 ${d}"
      rm -rf "${d}"
    fi
  done
}

# 回滚到指定版本：优先用已有镜像；否则用保留的 tgz 重建
rollback_to() {
  local ver="$1"
  if [ -z "${ver}" ]; then
    echo "USAGE: rollback_to <version>" >&2
    exit 1
  fi
  cd "${APP_DIR}"
  local COMPOSE=(docker compose)

  if docker image inspect "${IMAGE_NAME}:${ver}" >/dev/null 2>&1; then
    echo "==> 使用已有镜像回滚: ${IMAGE_NAME}:${ver}"
    docker tag "${IMAGE_NAME}:${ver}" "${IMAGE_NAME}:latest"
  else
    local tgz="${RELEASE_ROOT}/${ver}/backpack-quant.tgz"
    if [ ! -f "${tgz}" ]; then
      echo "ERROR: 无镜像 ${IMAGE_NAME}:${ver}，且缺少 ${tgz}" >&2
      list_versions
      exit 1
    fi
    echo "==> 镜像不在本地，从发布包重建: ${tgz}"
    local tmp
    tmp="$(mktemp -d)"
    tar -xzf "${tgz}" -C "${tmp}"
    if [ -f "${APP_DIR}/.env" ]; then
      cp -a "${APP_DIR}/.env" "${tmp}/.env"
    fi
    # 覆盖代码，保留 data/log/.env（不用 rsync，ECS 未必安装）
    find "${APP_DIR}" -mindepth 1 -maxdepth 1 \
      ! -name '.env' \
      ! -name 'backpack_quant_trading' \
      -exec rm -rf {} +
    # 同步顶层文件
    cp -a "${tmp}/." "${APP_DIR}/"
    # data/log 若被包内空目录覆盖，生产卷在 docker volume，宿主机目录可重建
    rm -rf "${tmp}"
    if [ ! -f "${APP_DIR}/backpack_quant_trading/frontend/dist/index.html" ]; then
      echo "ERROR: 发布包内缺少 frontend/dist" >&2
      exit 1
    fi
    export SKIP_MYSQL="${SKIP_MYSQL:-1}"
    export DEPLOY_VERSION="${ver}"
    export SKIP_RELEASE_TAG=1
    bash "${APP_DIR}/deploy/deploy.sh"
    docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:${ver}" || true
    write_current_version "${ver}"
    record_release_meta "${ver}" "" "rollback-rebuild"
    echo "==> 回滚重建完成: ${ver}"
    return 0
  fi

  write_current_version "${ver}"
  echo "==> 强制重建容器以切换镜像..."
  "${COMPOSE[@]}" up -d --force-recreate --no-deps api webhook dingtalk-agent

  echo "==> 等待 API 健康..."
  local ok=0 i=1
  while [ "${i}" -le 40 ]; do
    if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
      curl -s http://127.0.0.1:8100/api/health || true
      echo ""
      ok=1
      break
    fi
    sleep 5
    i=$((i + 1))
  done
  if [ "${ok}" != "1" ]; then
    echo "ERROR: 回滚后 API 未健康" >&2
    "${COMPOSE[@]}" logs --tail=80 api || true
    exit 1
  fi
  record_release_meta "${ver}" "" "rollback"
  echo "==> 回滚完成: ${ver}"
  list_versions
}

# CLI
cmd="${1:-}"
case "${cmd}" in
  make-version) make_version "${2:-}" ;;
  list) list_versions ;;
  tag) tag_image_version "${2:?version required}" ;;
  prune) prune_old_releases ;;
  rollback) rollback_to "${2:?version required}" ;;
  record)
    record_release_meta "${2:?version}" "${3:-}" "${4:-deploy}"
    write_current_version "${2}"
    ;;
  *)
    cat <<'USAGE'
Usage:
  deploy/versioning.sh make-version [gitsha]
  deploy/versioning.sh list
  deploy/versioning.sh tag <version>
  deploy/versioning.sh record <version> [gitsha] [mode]
  deploy/versioning.sh prune
  deploy/versioning.sh rollback <version>
USAGE
    exit 1
    ;;
esac

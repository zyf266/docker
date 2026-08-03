#!/bin/bash
# 所有 hotfix / restore 脚本必须 source 本文件。
# 正式服禁止 docker cp / 局部热更：易造成「路由新、策略旧、前端 dist 回退」。
# 唯一允许的更新路径：GitHub Actions → Deploy to Prod ECS (deploy-prod.yml)
#
# 紧急例外（需双人确认）：ALLOW_PROD_HOTFIX=1 bash deploy/xxx.sh
if [ "${ALLOW_PROD_HOTFIX:-}" = "1" ]; then
  echo "WARN: ALLOW_PROD_HOTFIX=1 — 紧急热更已放行，事后必须用 GitHub Actions 全量对齐。" >&2
  return 0 2>/dev/null || exit 0
fi

cat >&2 <<'EOF'
========================================================================
禁止正式服热更新（docker cp / 局部 scp / hotfix-*.sh）

原因：热更只覆盖部分文件，会导致：
  - trading.py 新、adaptive_long / binance_client 旧 → margin_type 报错
  - 宿主机旧 dist 覆盖容器 → 学习中心/文案回退
  - requirements 未进镜像 → No module named lighter

唯一允许的更新方式：
  GitHub → Actions → 「Deploy to Prod ECS」手动运行
  （workflow: .github/workflows/deploy-prod.yml）

紧急放行（不推荐）：
  ALLOW_PROD_HOTFIX=1 bash deploy/某个脚本.sh
  事后必须立刻跑一遍正式机 CI/CD 全量部署对齐版本。
========================================================================
EOF
exit 1

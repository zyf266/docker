# 正式服发布策略（禁止热更）

## 规则

1. **禁止**对正式机 `47.110.57.118` 做 `docker cp` / 局部 `scp` / 运行 `deploy/hotfix-*.sh` / `restore-prod-hotfixes.sh`。
2. **唯一允许**的正式服更新：GitHub Actions → **Deploy to Prod ECS**（`.github/workflows/deploy-prod.yml`，手动 `workflow_dispatch`）。
3. 热更会导致半套版本（路由新、策略旧、前端 dist 回退、依赖缺失），已多次造成生产故障。
4. 紧急例外仅当 `ALLOW_PROD_HOTFIX=1`，且事后必须立刻跑一遍正式机 CI/CD 全量对齐。

## Agent / 人工操作

- 发现正式服问题：在本地修代码 → commit / push → 触发 `Deploy to Prod ECS`。
- 不要再写「热更正式服」类脚本到生产执行路径。

## 前端构建（强制）

- **禁止**在正式/测试 ECS 的 Docker 构建阶段执行 `npm install` / `vite`（小内存易 OOM，表现为 `Exit handler never called` 或 `vite: not found`）。
- Actions 必须先跑 `deploy/build-frontend.sh`，把 `frontend/dist` 打进 `backpack-quant.tgz`；镜像只 `COPY` 预构建产物。
- 本地 `docker compose build` 前若无 dist：先执行 `bash deploy/build-frontend.sh`。

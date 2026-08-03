# 正式服发布策略（禁止热更）

## 规则

1. **禁止**对正式机 `47.110.57.118` 做 `docker cp` / 局部 `scp` / 运行 `deploy/hotfix-*.sh` / `restore-prod-hotfixes.sh`。
2. **唯一允许**的正式服更新：GitHub Actions → **Deploy to Prod ECS**（`.github/workflows/deploy-prod.yml`，手动 `workflow_dispatch`）。
3. 热更会导致半套版本（路由新、策略旧、前端 dist 回退、依赖缺失），已多次造成生产故障。
4. 紧急例外仅当 `ALLOW_PROD_HOTFIX=1`，且事后必须立刻跑一遍正式机 CI/CD 全量对齐。

## Agent / 人工操作

- 发现正式服问题：在本地修代码 → commit / push → 触发 `Deploy to Prod ECS`。
- 不要再写「热更正式服」类脚本到生产执行路径。

# 正式机 CI/CD（47.110.57.118）

与测试机（`39.106.143.222`，`Deploy to Test ECS`）分离。正式部署仅 **手动** `Deploy to Prod ECS`。

## 架构要点

| 项 | 正式机 |
|----|--------|
| 目录 | `/opt/backpack-quant` |
| DB | 宿主机已有 MySQL（`DB_HOST=host.docker.internal`） |
| 代理 | 宿主机 mihomo `:7891` → 容器 `HTTPS_PROXY` |
| 前端 | api `:8100` 静态；Nginx `/` → 8100 |
| Webhook | Nginx → `:8005` |
| 实例 RSA | `backpack_quant_trading/data/instance_rsa/`（私钥勿提交 Git；Docker `app_data` 卷持久化） |

## GitHub Secrets（正式）

| Secret | 说明 |
|--------|------|
| `SSH_HOST_PROD` | `47.110.57.118` |
| `SSH_USER_PROD` | 通常 `root` |
| `SSH_PRIVATE_KEY_PROD` | `github_actions_prod` 私钥全文 |
| `SSH_PORT_PROD` | 可选，默认 22 |

测试机仍用：`SSH_HOST` / `SSH_USER` / `SSH_PRIVATE_KEY` / `SSH_PORT`。

## 本机密钥（一次性）

```powershell
# 生成正式机专用密钥（勿覆盖测试机 github_actions）
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\github_actions_prod -N '""' -C "gha-prod-47"

# 公钥拷到正式机（需已有登录方式）
type $env:USERPROFILE\.ssh\github_actions_prod.pub | ssh root@47.110.57.118 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# 验证
ssh -i $env:USERPROFILE\.ssh\github_actions_prod root@47.110.57.118 "echo ok"
```

将私钥全文粘贴到 GitHub → Settings → Secrets → `SSH_PRIVATE_KEY_PROD`。

## 上线步骤

1. **首次**：把本仓库代码解压到正式机 `/opt/backpack-quant`（或先跑一次 Prod workflow）。
2. `bash deploy/bootstrap-prod-47.sh` — 查端口、代理、生成 `.env`。
3. 停旧栈（8100/8005/8050），**不杀** nginx / mihomo。
4. 编辑 `/opt/backpack-quant/.env`（外部 DB + 代理 + 业务 Key）。
5. 人工合并 `deploy/nginx/prod-443-snippet.conf` → `nginx -t` → reload。
6. Actions：Run workflow **Deploy to Prod ECS**。
7. `bash deploy/verify-prod.sh`。

## 相关文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/deploy-prod.yml` | 正式手动部署 |
| `.github/workflows/deploy.yml` | 测试（push main） |
| `deploy/bootstrap-prod-47.sh` | 正式机引导 |
| `deploy/verify-prod.sh` | 验收 |
| `deploy/nginx/prod-443-snippet.conf` | Nginx 片段（人工合并） |
| `deploy/env.prod.example` | 正式 `.env` 模板 |
| `docs/plans/2026-07-21-prod-cicd-47.md` | 执行计划 |

## 钉钉 Agent 口令（摘要）

| 场景 | 示例 |
|------|------|
| 监视 | `新增 ETH 2h 币种监视` / `当前监视状态` / `停止 ETH 币种监视` |
| 策略实例 | `查看策略实例` / `实例状态 <id>` / `确认停止实例 <id>` / `确认启动实例 <id>` / `实例日志` / `把实例 <id> 改成逐仓` |
| 确认下单 | `确认` / `确认 ord_xxx` / `取消` / `取消确认 ord_xxx` / `待确认列表` |
| 复盘 | `复盘 NVDA`（定时：每天 20:00 自动复盘，`AGENT_AUTO_REVIEW_DAYS`） |
| 周报 | `这周美股周报`；周六自动生成后若 `AGENT_WEEKLY_DINGTALK=1` 会推钉钉 |
| 日巡检 | 每天 `AGENT_PATROL_HOUR`（默认 9）点自动推送 |

**注意**：测试机 `dingtalk-agent` 保持 `restart=no`，避免与正式机抢同一钉钉 Stream。

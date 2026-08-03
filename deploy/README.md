# GitHub Actions → 阿里云 ECS

- **测试机**：`.github/workflows/deploy.yml`（`Deploy to Test ECS`）→ Secrets `SSH_HOST` 等；push `main` 或手动。
- **正式机**：见 [`README-prod.md`](README-prod.md)（`Deploy to Prod ECS`，仅手动；Secrets `SSH_*_PROD`）。

## 为什么不用服务器 git pull

ECS 上 `git` 访问 GitHub 会失败（`Empty reply from server`），网页 curl 能通也不代表 git 能用。

因此流程是：

1. Actions Runner `checkout`（国外，可访问 GitHub）
2. 打包后 **SCP** 到 ECS `/tmp/backpack-quant.tgz`
3. SSH 执行 `deploy/remote-ci.sh`：解压 → 装 Docker + 镜像加速 → `docker compose`

若构建时报 `registry-1.docker.io` / `i/o timeout`：说明未配镜像加速；`install-docker.sh` 会写入 `/etc/docker/daemon.json` 的 `registry-mirrors`。

若 `backpack-api is unhealthy`：先看 `docker compose logs api`。常见是缺 Python 依赖（如 `msgpack`）导致 gunicorn worker 启动失败。

若大量 API **500** 且 `backpack-mysql` 为 **Restarting (137)**：小内存 ECS（约 2GB）上 MySQL 被 OOM 杀掉。部署脚本会自动：

1. `deploy/ensure-swap.sh` — 创建并持久化 **2GB swap**（写入 `/etc/fstab`，重启后仍保留）
2. `deploy/mysql/conf.d/lowmem.cnf` — 限制 MySQL 内存占用
3. `docker-compose.yml` — `mem_limit`（mysql 512m / api 768m / webhook 384m）
4. API 默认 `GUNICORN_WORKERS=1`，后台调度用文件锁避免多 worker 重复跑

手动检查：`free -h`、`docker compose logs mysql --tail 50`、`dmesg -T | grep -i oom`

测试机触发：push `main` 或手动 Run workflow。正式机仅手动（见 README-prod）。

## Secrets（测试机）

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | 测试 ECS 公网 IP（如 `39.106.143.222`） |
| `SSH_USER` | 通常 `root` |
| `SSH_PRIVATE_KEY` | 私钥全文 |
| `SSH_PORT` | 可选，默认 22 |

正式机 Secrets 见 `README-prod.md`（`SSH_*_PROD`）。

本机验证 SSH：

```powershell
ssh -i $env:USERPROFILE\.ssh\github_actions root@<IP> "echo ok"
```

## 安全组

放行：22、8100、8005。

## 部署后

- `http://<IP>:8100/api/health`
- 首次会生成 `/opt/backpack-quant/.env`，业务 Key 自行 `nano` 编辑后 `docker compose up -d`

## 钉钉多 Agent（一期）

Compose 服务：`dingtalk-agent`（Stream）。**推荐新建独立机器人**，与旧 OpenClaw 小钉评分互不抢连接：

| 变量 | 用途 |
|------|------|
| `DINGTALK_AGENT_BOT_CLIENT_ID` / `SECRET` | 新 Agent 机器人（ECS `dingtalk-agent` 优先用这个） |
| `DINGTALK_SCORE_BOT_CLIENT_ID` / `SECRET` | 旧评分机器人（本机 OpenClaw / 旧进程继续用） |
| `DINGTALK_AGENT_ALLOW_LEGACY_SCORE` | 默认 `0`：新机器人不接「信号评分」 |
| `AGENT_ORCH_ENABLED` | 默认 `1`；设 `0` 关闭 Agent 编排 |

未配置 `DINGTALK_AGENT_BOT_*` 时会回退到 `DINGTALK_SCORE_BOT_*`（易抢 Stream，不推荐）。

钉钉开放平台操作：创建企业内部应用 → 机器人 → 开启 Stream 模式 → 拿到 Client ID/Secret → 群内添加该机器人。

钉钉指令示例：

| 指令 | 作用 |
|------|------|
| `@美股分析师 NVDA` | 美股报告（建议+支撑压力） |
| `@A股分析师 茅台` | A股报告 |
| `@加密分析师 BTC` | 加密报告 |
| `看看茅台+BTC` | 协调拆单 |
| `@信息检索 NVDA` | 固定源新闻 |
| `纠正偏好：更严止损` | 全局风格记忆 |
| `复盘 NVDA` | 复盘历史建议 |
| `确认` / `确认 ord_xxx` | 确认**本人**待执行订单（需 `WEBHOOK_SECRET` + `AGENT_EXEC_INSTANCE_ID`） |
| `@风控 100x满仓` / `@风控 放行 BTC` | 启发式风控审查 / 放行 |

确认下单走专用接口 `POST /webhook/agent-confirm`（强制验签、禁止广播）。未配置实例 ID 时只 dry-run。

本地烟雾测试：

```powershell
$env:AGENT_E2E_MOCK_LLM=1
python backpack_quant_trading/tools/agent_e2e_smoke.py
```

信号旁路 Agent 推送默认关：`AGENT_SIGNAL_PUSH_ENABLED=0`；设为 `1` 可额外推送（不删旧评分推送）。T13 钩子见 `agents/scheduler_hooks.py`，需业务侧手动调用，**尚未挂到 api/main 定时循环**。

## 相关文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/deploy.yml` | 测试机 checkout → SCP → SSH |
| `.github/workflows/deploy-prod.yml` | 正式机（仅手动） |
| `deploy/README-prod.md` | 正式机引导与 Secrets |
| `deploy/remote-ci.sh` | 解压 + 装 Docker + 调用 deploy.sh |
| `deploy/deploy.sh` | `docker compose` 构建重启 |
| `deploy/install-docker.sh` | 阿里云源安装 Docker |
| `docs/plans/2026-07-16-agent-dingtalk-multi-analyst.md` | Agent 一期执行计划 |
| `backpack_quant_trading/agents/` | 多 Agent 编排 |

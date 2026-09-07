---
name: deploy-prod-verify
description: >-
  Post-deploy verification checklist for prod ECS 47.110.57.118 backpack-quant.
  Use after GitHub Actions Deploy to Prod ECS, when user asks to verify生产、验收发布、
  检查正式服、重启后健康检查、5001/8100/dingtalk-agent.
---

# 正式服 Deploy 后验收（Harness SOP）

## 硬规则

- **禁止** hotfix / `docker cp` / 服务器上改 `.py`
- 唯一代码路径：本地 → commit/push → Actions **Deploy to Prod ECS**
- 允许：查日志、health、经用户同意改 `.env`、数据导入

## 验收清单（SSH 上执行，贴输出）

```bash
# 1) 容器
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'backpack-(api|webhook|dingtalk-agent)' || true

# 2) API
curl -sf http://127.0.0.1:8100/health || curl -sf http://127.0.0.1:8100/api/health || true

# 3) tradingview_bot :5001（宿主机进程）
ss -tlnp | grep -E '5001|5002'
curl -sf http://127.0.0.1:5001/health

# 4) 钉钉 Stream Agent 日志（最近是否连上）
docker logs backpack-dingtalk-agent --tail 30 2>&1 | tail -30

# 5) 若本次含 A股 AI Agent
docker logs backpack-api --tail 50 2>&1 | grep -iE 'a.share|a_share|startup' | tail -20
```

## 功能冒烟（按改动选做）

| 改动面 | 冒烟 |
|--------|------|
| TV 新 ID | `curl` POST `5001/webhook` 带该 id，看钉钉群 |
| A股 AI Agent | 网页启动任务；钉钉是否推卡片；纠偏 @Stream 机器人 |
| 前端 | 浏览器硬刷新策略页，看新文案/看板 |
| dingtalk-agent | @机器人 发「怎么用」，应回菜单而非超时 |

## 汇报模板

```markdown
### Deploy 验收
- Actions: <成功/失败链接>
- 容器状态: ...
- 5001 health: ...
- 冒烟: ...
- 未验证风险: ...
```

## 失败处理

- Actions 失败：修 CI / 前端 build，**不要**热更绕过
- 5001 未监听：按既有方式重启 `tradingview_bot.py`（宿主机），勿 docker cp

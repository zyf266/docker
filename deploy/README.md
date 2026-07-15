# GitHub Actions → 阿里云 ECS

## 为什么不用服务器 git pull

ECS 上 `git` 访问 GitHub 会失败（`Empty reply from server`），网页 curl 能通也不代表 git 能用。

因此流程是：

1. Actions Runner `checkout`（国外，可访问 GitHub）
2. 打包后 **SCP** 到 ECS `/tmp/backpack-quant.tgz`
3. SSH 执行 `deploy/remote-ci.sh`：解压 → 装 Docker（阿里云源）→ `docker compose`

触发方式仍是：push `main` 或手动 Run workflow。Secrets 仍是 `SSH_HOST` / `SSH_USER` / `SSH_PRIVATE_KEY` / `SSH_PORT`。

## Secrets

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | ECS 公网 IP |
| `SSH_USER` | 通常 `root` |
| `SSH_PRIVATE_KEY` | 私钥全文 |
| `SSH_PORT` | 可选，默认 22 |

本机验证 SSH：

```powershell
ssh -i $env:USERPROFILE\.ssh\github_actions root@<IP> "echo ok"
```

## 安全组

放行：22、8100、8005。

## 部署后

- `http://<IP>:8100/api/health`
- 首次会生成 `/opt/backpack-quant/.env`，业务 Key 自行 `nano` 编辑后 `docker compose up -d`

## 相关文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/deploy.yml` | checkout → SCP → SSH |
| `deploy/remote-ci.sh` | 解压 + 装 Docker + 调用 deploy.sh |
| `deploy/deploy.sh` | `docker compose` 构建重启 |
| `deploy/install-docker.sh` | 阿里云源安装 Docker |

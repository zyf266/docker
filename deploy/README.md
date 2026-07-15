# GitHub Actions → 阿里云 ECS CI/CD

推送到 `main` 后，Actions 通过 SSH 登录服务器，执行 `git pull` + `docker compose`。

## 当前卡点（必须先解决）

Actions 约 15 秒失败、本机 SSH 也报：

```text
Permission denied (publickey,...)
```

说明：**GitHub Secrets 里的私钥，和 ECS 上 `authorized_keys` 里的公钥还没配对。**

流程本身没坏，是密钥没配通。

---

## 修复步骤（按顺序做）

### 1. 本地生成一对密钥（若还没有）

PowerShell：

```powershell
ssh-keygen -t ed25519 -C "github-actions" -f $env:USERPROFILE\.ssh\github_actions -N '""'
```

### 2. 公钥放到 ECS（阿里云 Workbench 终端，root）

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# 粘贴本地 github_actions.pub 的整行内容，保存
chmod 600 ~/.ssh/authorized_keys
```：wq

查看公钥：

```powershell
Get-Content $env:USERPROFILE\.ssh\github_actions.pub
```

### 3. 私钥放到 GitHub Secret

仓库 → **Settings → Secrets and variables → Actions**：

| Secret | 值 |
|--------|------|
| `SSH_HOST` | `39.106.143.222` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | 私钥全文（见下） |
| `SSH_PORT` | `22`（可不配，workflow 默认 22） |

查看私钥：

```powershell
Get-Content $env:USERPROFILE\.ssh\github_actions
```

必须从 `-----BEGIN` 到 `-----END` **整段复制**，不要少行、不要加引号。

### 4. 安全组放行 22

阿里云 ECS 安全组入方向：TCP **22**（来源可先 `0.0.0.0/0`，通了再收紧）。

### 5. 本机先验证 SSH（可选但推荐）

```powershell
ssh -i $env:USERPROFILE\.ssh\github_actions root@39.106.143.222 "echo ok"
```

能打出 `ok` 再去跑 Actions。

### 6. 重新触发部署

- Actions → **Deploy to ECS** → **Run workflow**
- 或再 push 一次 `main`

---

## 成功后访问

- 健康检查：`http://39.106.143.222:8100/api/health`
- 页面：`http://39.106.143.222:8100`

首次部署会在服务器生成 `/opt/backpack-quant/.env`，交易/钉钉等 Key 按需手动编辑。

## 若仓库是私有的

ECS 上 `git clone/fetch` 需要能访问 GitHub。二选一：

1. 仓库设为 **Public**（最简单）
2. 或在服务器配置 [Deploy Key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)（只读），并把 workflow / bootstrap 里的 clone URL 改成 `git@github.com:zyf266/docker.git`

## 常见失败

| 现象 | 处理 |
|------|------|
| `ssh: no key found` | Secret 私钥格式错误，用记事本重贴 |
| `Permission denied (publickey)` | 公钥未写入 ECS |
| `get.docker.com` / `SSL_ERROR_SYSCALL` | 国内访问官方安装脚本失败；用 `deploy/install-docker.sh`（阿里云源），**须先 push 再跑 Actions** |
| `Empty reply from server` / 无法 clone GitHub | ECS 访问不了 github.com；workflow 已改用 gitclone/ghproxy 镜像拉取，**须先 push 再跑 Actions** |
| 健康检查失败 | `docker compose logs api`；安全组放行 8100 |

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/deploy.yml` | SSH 到 ECS → 装 Docker → `deploy.sh` |
| `deploy/install-docker.sh` | 国内 ECS 安装 Docker（阿里云镜像） |
| `deploy/deploy.sh` | `git pull` + `docker compose` |
| `deploy/bootstrap-server.sh` | 空白机一次性初始化 |
| `docker-compose.yml` / `Dockerfile` | 容器编排 |

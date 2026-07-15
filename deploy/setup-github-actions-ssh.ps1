# 生成 GitHub Actions → ECS 部署用 SSH 密钥，并打印 Secrets 填写说明
# 用法: powershell -ExecutionPolicy Bypass -File deploy/setup-github-actions-ssh.ps1

$ErrorActionPreference = "Stop"
$keyPath = Join-Path $env:USERPROFILE ".ssh\github_actions"
$pubPath = "$keyPath.pub"

if (-not (Test-Path (Join-Path $env:USERPROFILE ".ssh"))) {
    New-Item -ItemType Directory -Path (Join-Path $env:USERPROFILE ".ssh") | Out-Null
}

if (Test-Path $keyPath) {
    Write-Host "已存在密钥: $keyPath （跳过生成）"
} else {
    ssh-keygen -t ed25519 -C "github-actions-deploy" -f $keyPath -N '""'
    Write-Host "已生成: $keyPath"
}

Write-Host ""
Write-Host "========== 1) GitHub Secret: SSH_PRIVATE_KEY =========="
Write-Host (Get-Content $keyPath -Raw)
Write-Host "========== 2) 写入 ECS ~/.ssh/authorized_keys 的公钥 =========="
Write-Host (Get-Content $pubPath -Raw)
Write-Host "========== 3) 其他 Secrets =========="
Write-Host "SSH_HOST = 你的 ECS 公网 IP"
Write-Host "SSH_USER = root"
Write-Host "SSH_PORT = 22   (可选)"
Write-Host ""
Write-Host "服务器命令示例:"
Write-Host "  mkdir -p ~/.ssh && chmod 700 ~/.ssh"
Write-Host "  echo '上面的公钥一行' >> ~/.ssh/authorized_keys"
Write-Host "  chmod 600 ~/.ssh/authorized_keys"

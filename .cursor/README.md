# Cursor Agent Harness（本仓库）

提升 Agent 效率与安全边界：Hooks 强制护栏 + Skills SOP + Rules 分模块上下文。

## 结构

```
.cursor/
  hooks.json                 # 事件绑定
  hooks/                     # Python hooks（Windows/Linux 通用）
  harness-state.json         # 会话编辑跟踪（gitignore）
  rules/                     # always + globs 规则
  skills/                    # 项目级 SOP
```

## Hooks

| 事件 | 脚本 | 作用 |
|------|------|------|
| beforeShellExecution | block_prod_hotfix.py | 拦截正式服热更 / docker cp 源码 |
| beforeSubmitPrompt | scan_prompt_secrets.py | 提示疑似密钥 |
| afterFileEdit | track_file_edit.py | 记录待验标签 |
| stop | stop_verification.py | 提醒贴验证证据 |

自测：`python .cursor/hooks/self_test.py`

## Skills（自动/按描述触发）

- `tv-webhook-branch` — TV ID→钉钉群
- `deploy-prod-verify` — Deploy 后验收
- `a-share-ai-feedback` — 纠偏收录
- `pre-pr-review` — PR 前两轮审查

## 使用建议

1. 大改动用 `/plan` → `/exec`
2. 完成后看 stop 提醒是否跑测试
3. Deploy 后说「按 deploy-prod-verify 验收」
4. Hooks 不生效时：Cursor Settings → Hooks，或重启 Cursor

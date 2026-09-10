# Cursor Agent Harness（本仓库）

提升 Agent 效率与安全边界：Hooks 强制护栏 + Skills SOP + Rules 分模块上下文 + 本地开发记忆。

## 结构

```
.cursor/
  hooks.json                 # 事件绑定
  hooks/                     # Python hooks（Windows/Linux 通用）
  harness-state.json         # 会话编辑跟踪（gitignore）
  rules/                     # always + globs 规则
  skills/                    # 项目级 SOP
  mcp.json                   # 项目 MCP（dev-memory）
  memory_lib/                # 本地 Chroma 开发记忆
  dev-memory/                # 向量库落盘（gitignore）
```

## Hooks

| 事件 | 脚本 | 作用 |
|------|------|------|
| sessionStart | session_inject_dev_memory.py | 尽力注入置顶/近期记忆 |
| beforeShellExecution | block_prod_hotfix.py | 拦截正式服热更 / docker cp 源码 |
| beforeSubmitPrompt | scan_prompt_secrets.py | 提示疑似密钥 |
| afterFileEdit | track_file_edit.py | 记录待验标签 |
| stop | stop_verification.py | 提醒贴验证证据 |

自测：`python .cursor/hooks/self_test.py`

## 开发记忆（Cursor 侧）

跨对话记住约定 / 踩坑 / 决策 / 未完成任务。可靠路径是 MCP（或 CLI），sessionStart 注入为尽力而为。

```bash
python .cursor/memory_lib/cli.py upsert --kind convention --text "禁止生产热更，走 Deploy"
python .cursor/memory_lib/cli.py search --query "热更"
python .cursor/memory_lib/cli.py stats
```

MCP：Settings → MCP 启用 `dev-memory`（需 `pip install mcp chromadb`）。

## Skills（自动/按描述触发）

- `dev-memory` — 本地向量记忆 search/upsert
- `tv-webhook-branch` — TV ID→钉钉群
- `deploy-prod-verify` — Deploy 后验收
- `a-share-ai-feedback` — 纠偏收录
- `pre-pr-review` — PR 前两轮审查

## 使用建议

1. 大改动用 `/plan` → `/exec`
2. 任务开始先 `memory_search`；重要结论 `memory_upsert`
3. 完成后看 stop 提醒是否跑测试
4. Deploy 后说「按 deploy-prod-verify 验收」
5. Hooks 不生效时：Cursor Settings → Hooks，或重启 Cursor

---
name: dev-memory
description: >-
  Cursor local Chroma dev memory: search/upsert decisions, bugfixes, conventions,
  tasks across chats. Use when starting coding tasks, user says 记住/以后都/结论,
  hard bugs fixed, or unfinished work must persist. MCP tools memory_search /
  memory_upsert / memory_delete / memory_stats.
---

# Cursor 开发记忆（本地 Chroma）

跨对话持久化本仓库约定、踩坑、决策与未完成任务。数据在 `.cursor/dev-memory/`（gitignore），**不进正式服**。

## 何时用

| 时机 | 动作 |
|------|------|
| 编码任务开始 | 先 `memory_search`（用户问题 + 模块关键词），再改代码 |
| 用户说「记住 / 以后都 / 结论是」 | `memory_upsert` |
| 难查 bug 已修好 | `memory_upsert` kind=`bugfix` |
| 会话结束有未完成项 | `memory_upsert` kind=`task` |

## kind

`decision` | `bugfix` | `convention` | `task` | `session`

## 禁止写入

密钥、私钥、`.env`、Webhook token、生产登录口令（store 层也会拒）。

## CLI（MCP 未启用时）

```bash
python .cursor/memory_lib/cli.py search --query "热更"
python .cursor/memory_lib/cli.py upsert --kind convention --text "禁止生产热更，走 Deploy"
python .cursor/memory_lib/cli.py stats
```

## MCP

项目 [`.cursor/mcp.json`](../../mcp.json) 注册 `dev-memory`。若工具不可见：Cursor Settings → MCP → 启用并 `pip install mcp chromadb`。

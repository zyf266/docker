---
name: a-share-ai-feedback
description: >-
  A-share AI adaptive agent DingTalk feedback / RAG draft / style confirm flow.
  Use when user asks about 纠偏、点评、钉钉回复信号、刷新并生效风格、@OpenClaw、
  Stream 机器人收录、待确认草稿.
---

# A股 AI 纠偏收录（Harness SOP）

## 角色分工

| 对象 | 作用 | 能否收评 |
|------|------|----------|
| Webhook「自定义」 | 只推 ActionCard | ❌ |
| Stream 机器人（OpenClaw小盯 / Agent Bot） | `dingtalk-agent` 长连接 | ✅ 必须 @ 它 |

## 用户正确操作

1. **引用**买入/卖出卡片（不要只 @ 而无引用）
2. **@ Stream 机器人**（可不同时 @ 自定义）
3. 写点评：如「位置没问题」「其实可以买」
4. 成功回执：先「收到，正在记录…」再「纠偏已收录」
5. 网页策略页 → 「待确认」可见 → 点「刷新并生效风格」→ 群里「纠偏已生效」

## Agent 排障顺序

1. 正式服是否已 Deploy 含 `a_share_ai_agent_feedback` 的代码？
2. `docker logs backpack-dingtalk-agent` 是否有入站 / `a_share_ai`？
3. 是否回了 `usage_hint` 菜单？→ 未命中卡片上下文，检查 ActionCard 引用解析
4. 白名单 `DINGTALK_MANUAL_SCORE_ALLOWED_STAFF_IDS` 是否拦了发送者？

## 相关文件

- `core/a_share_ai_agent_feedback.py`
- `dingtalk_score_bot.py`（路由优先于 Agent 菜单）
- `core/dingtalk_manual_score.py`（`_summarize_replied_msg` ActionCard）
- 前端 `AShareAiAgent.jsx` 草稿区

## 禁止

- 告诉用户「@自定义就能收录」
- 未 Deploy 就声称正式服已可纠偏

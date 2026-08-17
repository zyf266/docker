# A股 AI 自适应策略 Agent — 执行计划（2026-08-17）

## 目标

- 多任务：30m / 60m / 日线，交易时段扫描，**15:00 后不推送**
- 决策：基本面（24h 缓存）> 量能 > 其它技术；LLM JSON；硬规则 T+1/涨停禁买/跌停禁卖
- 钉钉：OpenClaw **ActionCard** 精致卡片；自然语言点评 → RAG；**人工确认**后才改风格
- 回测：最长 1 年、可选区间、同样调 LLM；K 线标注买卖点
- 前端：策略矩阵新 banner + 独立页（任务/回测/偏好确认）

## 非目标（一期）

- 实盘下单
- 自动热改 Prompt（必须人工确认）
- 海报位图渲染（先用 ActionCard）

## 任务

### T1：计划（本文件）
### T2：核心 `core/a_share_ai_agent.py` — Prompt/硬规则/基本面缓存/扫描服务
### T3：`send_action_card` + OpenClaw Webhook 环境变量
### T4：API `api/routers/a_share_ai_agent.py` + main 挂载 + DB 配置
### T5：点评反馈写入 RAG + 偏好确认接口
### T6：回测 API（LLM 逐步/采样）+ 信号点
### T7：前端页面 + StrategyMatrix banner
### T8：冒烟

## 环境变量

```
A_SHARE_AI_AGENT_DINGTALK_WEBHOOK=...
A_SHARE_AI_AGENT_DINGTALK_KEYWORD=信号
```

（密钥勿提交 Git）

## 执行顺序

- [x] T1
- [x] T2–T7（核心/钉钉/API/偏好确认/回测/前端 banner）
- [x] T8 冒烟：硬规则 + ActionCard 文案组装
- [x] T9 钉钉 Stream 自动收评 → 偏好草稿（人工确认后生效）

## 闭环补充（2026-08-17 用户澄清）

- [x] **每轮扫描必推钉钉**（买入 / 不买入·观望 / 卖出），`thesis` 强制非空
- [x] 数据不足或 LLM 失败时，仍推「不买入」占位卡并写明原因
- [x] Stream 回复纠偏（含反驳观望、主张可买）→ RAG + 草稿
- [x] 网页 **「刷新并生效风格」** → 合并草稿、写 `style_addendum`，下一轮 `_prefs_block()` 并入提示词

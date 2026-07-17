# Agent 化一期：钉钉多分析师 + Chroma 记忆 + 检索/协调/风控/执行/复盘

> 日期：2026-07-16  
> 来源：brainstorm 冻结需求  
> 建议执行：`/exec` → executing-plans（大改建议先 worktree）

## 背景与目标

将现有「统一口吻」的美股/加密评分与钉钉 Stream 机器人，升级为 **多 Agent 分工**：分市场分析师、信息检索、协调路由、风控、确认后执行、复盘；并用 **同一 Chroma 实例、不同 collection** 做长期记忆与全局风格学习。

**入口**：仅钉钉（前缀点名 + 协调自动路由）  
**量级**：约 20 次/天  
**与旧系统**：并存，验收后再关旧入口  

## 验收标准（演示即过）

1. 钉钉 `@美股分析师` / `@A股分析师` / `@加密分析师` 各出一份含 **买卖建议 + 支撑/压力** 的报告  
2. `@信息检索` 能从 **固定源 B** 查出新闻，并被分析师 **引用**  
3. 纠正一次后，同一风格偏好在 **其它标的** 上也能体现（全局学习）  
4. 协调 Agent 能把「茅台+BTC」拆给两个分析师  
5. 风控 Agent 能对明显过激信号给出 **拒绝理由**  
6. 执行 Agent：仅当用户钉钉回复 **「确认」** 后才对接 webhook 下单（可演示到「待确认」卡片；真下单需有测试实例）

## 架构落点（复用优先）

| 能力 | 复用 | 新建 |
|------|------|------|
| 钉钉 Stream @ | `dingtalk_score_bot.py`、`dingtalk_manual_score.py` | 扩展 `_dispatch` 多 Agent 路由 |
| 加密/美股评分与 K 线 | `crypto_signal_scorer.py`、`us_stock_signal_scorer.py`、`signal_asset_router.py` | 包一层「分析师 Persona + 报告 schema」 |
| A 股 | `stock_ai.py`、`stock_kline_cache.py` | `a_share_analyst` Agent |
| 新闻固定源 | `stock_news_feeds.py`、`us_stock_news.py` | `agent_research` 统一检索接口（本期不上通用搜索 Key） |
| Chroma | `score_feedback_store.py`（collection=`score_feedback`） | `agent_memory_store.py`：`agent_prefs` / `agent_reports` / `agent_research` / `agent_reviews` |
| 下单 | `webhook_service.py` `:8005/webhook` | `execution_agent`：待确认队列 + 「确认」消费 |
| 推送 | `send_dingtalk_markdown()` | Agent 报告 Markdown 模板 |

```
钉钉 @消息
  → dingtalk_score_bot（扩展）
  → CoordinatorAgent（前缀 / 自动识别）
  → [ResearchAgent] → 固定源 → Chroma agent_research
  → MarketAnalyst(US|A|Crypto) + RAG(prefs/reports/reviews)
  → RiskAgent（过激则 reject+理由）
  → 推送报告；若含「建议执行」→ ExecutionAgent 待确认
  → 用户「确认」→ webhook
  → 用户纠正 → MemoryWriter（全局 prefs）
  → ReviewAgent（异步/定时）→ agent_reviews
```

## 固定源 B（本期检索白名单）

| 市场 | 源（复用现有 fetcher） |
|------|------------------------|
| 美股 | Yahoo ticker 新闻、`us_stock_news`、金十（若相关） |
| A股 | 东财 / 同花顺 / 新浪（`stock_news_feeds`） |
| 加密 | 金十闪讯关键词 + 已有加密相关 feed（无 Serper/Tavily） |

通用搜索 API（A）**预留接口**，本期不配 Key、不调用。

## 环境变量（计划新增，勿提交密钥）

```bash
# Agent 总开关
AGENT_ORCH_ENABLED=1
# Chroma（复用路径，新 collection）
AGENT_MEMORY_CHROMA_ENABLED=1
# 可选：与 SCORE_FEEDBACK 同目录
# SCORE_FEEDBACK_CHROMA_PATH=backpack_quant_trading/data/chroma_score_feedback
# 执行确认超时（分钟）
AGENT_EXEC_CONFIRM_TTL_MIN=30
```

旧：`DINGTALK_SCORE_BOT_*`、`SCORE_FEEDBACK_CHROMA_*`、`CRYPTO_SCORE_ENABLED` 保持。

---

## 任务列表

### T1：Agent 包骨架与类型定义

- **文件**:  
  - `backpack_quant_trading/agents/__init__.py`（新建）  
  - `backpack_quant_trading/agents/types.py`（新建）  
- **改动**: 定义 `AgentId`、`AnalyzeRequest`、`AnalyzeReport`（含 `action`/`support`/`resistance`/`rationale`/`citations`/`risk_decision`）、`MemoryKind`；不写业务逻辑  
- **验证**: `python -c "from backpack_quant_trading.agents.types import AnalyzeReport; print(AnalyzeReport.__annotations__)"`  
- **完成标准**: 可导入；字段覆盖验收报告所需项  

### T2：Chroma 多 collection 记忆层

- **文件**:  
  - `backpack_quant_trading/core/agent_memory_store.py`（新建）  
  - 复用路径逻辑参考 `core/score_feedback_store.py`  
- **改动**:  
  - collections: `agent_prefs` / `agent_reports` / `agent_research` / `agent_reviews`  
  - API: `upsert_memory(kind, id, document, metadata)`、`query_memory(kind, text, n, filters)`  
  - **不改** `score_feedback` collection  
- **验证**: 本地临时目录 upsert + query 一条 prefs，断言命中  
- **完成标准**: 与评分反馈同 path 时可并存；开关 `AGENT_MEMORY_CHROMA_ENABLED`  

### T3：全局偏好写入/检索（钉钉纠正 → prefs）

- **文件**:  
  - `backpack_quant_trading/agents/memory.py`（新建）  
  - 轻量扩展 `core/score_feedback.py` **或** 独立 `is_agent_feedback_command`（避免与旧评分纠正冲突）  
- **改动**:  
  - `save_global_preference(text, agent_id, staff_id)` → `agent_prefs`  
  - `retrieve_global_preferences(agent_id, query, n=5)` → 注入 prompt  
  - 元数据含 `scope=global`，**不按 symbol 过滤**（满足「其它标的也体现」）  
- **验证**: 写入「更严止损」后，用不同 symbol 的 query 仍能检索到  
- **完成标准**: 全局检索不依赖 symbol 相等  

### T4：信息检索 Agent（固定源 B）

- **文件**:  
  - `backpack_quant_trading/agents/research_agent.py`（新建）  
  - 调用 `core/stock_news_feeds.py`、`core/us_stock_news.py`  
- **改动**:  
  - `research(symbol, market) -> list[Citation]`  
  - 结果 upsert 到 `agent_research`  
  - 预留 `GenericSearchProvider` 空实现（A 类 Key）  
- **验证**: `research("600519", "a_share")` / `research("NVDA", "us_stock")` 返回非空或明确「源无数据」结构（不抛未捕获异常）  
- **完成标准**: 返回结构含 `title/url/snippet/source`；失败可降级  

### T5：三个市场分析师（Persona + 报告）

- **文件**:  
  - `backpack_quant_trading/agents/analysts/us_analyst.py`  
  - `backpack_quant_trading/agents/analysts/a_share_analyst.py`  
  - `backpack_quant_trading/agents/analysts/crypto_analyst.py`  
  - `backpack_quant_trading/agents/analysts/base.py`（共用：拉 K 线、调 DeepSeek、套 RAG）  
- **改动**:  
  - 各自 system prompt（风格独立）  
  - 输出强制 JSON → `AnalyzeReport`（买卖建议 + 支撑/压力）  
  - 复用现有 K 线/指标：美股 Massive、加密 HL、A 股 cache/`stock_ai`  
  - 注入 `retrieve_global_preferences` + 可选 research citations  
  - **不做**真实下单  
- **验证**: 各分析师对固定 symbol 跑通一次（可用 mock LLM 或小积分真实调用）；断言有 support/resistance 字段  
- **完成标准**: 三个模块可独立 `analyze(req) -> AnalyzeReport`  

### T6：风控 Agent（一期凭经验）

- **文件**: `backpack_quant_trading/agents/risk_agent.py`（新建）  
- **改动**:  
  - 输入：分析师报告 + 可选账户摘要  
  - 输出：`allow | reject` + `reason`  
  - 启发式规则示例（可配置阈值，默认偏严演示）：过高杠杆暗示、无止损、与 prefs 冲突、「满仓梭哈」话术等  
  - 明确标注 `mode=heuristic_v1`  
- **验证**: 构造「建议 100x 全仓无止损」→ reject；正常报告 → allow  
- **完成标准**: 拒绝时理由可读，供钉钉展示  

### T7：协调 / 路由 Agent

- **文件**: `backpack_quant_trading/agents/coordinator.py`（新建）  
- **改动**:  
  - 解析前缀：`美股分析师|A股分析师|加密分析师|信息检索|风控|复盘|执行`  
  - 无前缀：识别标的列表（茅台/600519、BTC、NVDA）→ 拆成多个 `AnalyzeRequest`  
  - 「茅台+BTC」→ A股 + 加密 两个子任务  
  - 编排顺序：research（按需）→ analyst(s) → risk → 格式化回复  
- **验证**: 单测字符串路由用例 5 条（含拆单）  
- **完成标准**: 拆单返回 ≥2 个子报告摘要  

### T8：执行 Agent（确认后下单）

- **文件**:  
  - `backpack_quant_trading/agents/execution_agent.py`（新建）  
  - `backpack_quant_trading/data/agent_pending_orders.json`（运行时）  
- **改动**:  
  - `propose_order(report) -> pending_id`（不调用 webhook）  
  - `confirm_order(pending_id|latest, staff_id)` → `POST` 本地 webhook（`WEBHOOK_BASE` 默认 `http://127.0.0.1:8005/webhook`）构造安全 payload（`manual_test` 或专用标记）  
  - TTL：`AGENT_EXEC_CONFIRM_TTL_MIN`  
  - 无 pending / 过期 → 明确错误文案  
- **验证**: propose 后未 confirm 时 webhook 未被调用（可用 mock）；confirm 后请求体字段正确  
- **完成标准**: 钉钉话术区分「待确认」与「已提交」  

### T9：复盘 Agent

- **文件**: `backpack_quant_trading/agents/review_agent.py`（新建）  
- **改动**:  
  - 从 `agent_reports` 取历史建议，对比当前价/简易收益  
  - 写入 `agent_reviews`；摘要可进 prefs 候选（可选自动，默认仅存储）  
- **验证**: 对一条假历史报告跑 `review()` 得到 structured 结果  
- **完成标准**: 钉钉 `@复盘` 或协调识别「复盘 NVDA」可触发  

### T10：报告 Markdown 与钉钉推送格式

- **文件**: `backpack_quant_trading/agents/formatters.py`（新建）  
- **改动**: 统一模板：标题 Agent 名、标的、建议、支撑/压力、引用列表、风控结论、待确认 CTA  
- **验证**: 对样例 `AnalyzeReport` 渲染非空 markdown  
- **完成标准**: 长度适合钉钉（必要时截断 citations）  

### T11：扩展钉钉 Stream 入口（并存旧评分）

- **文件**:  
  - `backpack_quant_trading/dingtalk_score_bot.py`  
  - 可选薄封装 `backpack_quant_trading/agents/dingtalk_bridge.py`  
- **改动**:  
  - `_dispatch` 增加分支：若 `AGENT_ORCH_ENABLED` 且命中 Agent 前缀/协调意图 → `coordinator.handle`  
  - **保留** 原 `is_feedback_command` / `is_manual_score_command` 路径（迁移策略 C）  
  - 新纠正：`纠正偏好：…` / `@美股分析师 你太保守了` → `save_global_preference`  
- **验证**: 本地用构造 raw dict 调 bridge（不连真钉钉）跑通路由  
- **完成标准**: 旧「评分 XXX」仍可用；新前缀走 Agent  

### T12：Docker / 进程接入

- **文件**:  
  - `deploy/entrypoint.sh` 或 `docker-compose.yml`（新增 service `dingtalk-agent` **或** 在 api startup 内嵌线程——二选一，推荐 **独立 command**）  
  - `deploy/env.example`  
- **改动**:  
  - 推荐：`command: ["python", "-m", "backpack_quant_trading.dingtalk_score_bot"]` 的 compose service，挂载 `app_data`（Chroma 同卷）  
  - 写入 `AGENT_*` 到 env.example  
  - mem_limit 建议 256m～384m（Stream 客户端较轻）  
- **验证**: `docker compose config` 通过；文档说明需配置 Stream Client  
- **完成标准**: 云上可与 api/mysql/webhook 一并启动（密钥已有则可连）  

### T13：定时/信号触发（与现有扫描并存）

- **文件**:  
  - `api/main.py` 或 `agents/scheduler_hooks.py`  
  - 轻量挂钩 `crypto_signal_hub` / 现有评分推送成功回调  
- **改动**:  
  - 定时或信号事件 → 按资产选分析师 → 推钉钉（带 Agent 署名）  
  - **不删除**旧 `push_score_to_dingtalk`；用开关 `AGENT_REPLACE_LEGACY_PUSH=0` 默认关  
- **验证**: 手动调用 hook 一次产生 Agent 格式消息（可 dry-run 只写日志）  
- **完成标准**: 文档说明如何打开 Agent 推送  

### T14：端到端验收脚本（无真下单）

- **文件**: `backpack_quant_trading/tools/agent_e2e_smoke.py`（新建）  
- **改动**: 命令行模拟：  
  1. 三市场 analyze  
  2. research 引用非空或明确降级  
  3. 写入 prefs 后再 analyze 其它标的，prompt/报告含偏好痕迹  
  4. 「茅台+BTC」拆单  
  5. 过激报告 → risk reject  
  6. propose 订单状态为 pending  
- **验证**: `python backpack_quant_trading/tools/agent_e2e_smoke.py`（可用 `AGENT_E2E_MOCK_LLM=1`）  
- **完成标准**: 退出码 0；打印五条验收对应 PASS  

### T15：文档与运维说明

- **文件**:  
  - `deploy/README.md`  
  - `docs/plans/2026-07-16-agent-dingtalk-multi-analyst.md`（本文勾选更新）  
- **改动**: 钉钉指令表、collection 名、开关、回滚（`AGENT_ORCH_ENABLED=0`）  
- **验证**: 文档内指令与代码前缀一致  
- **完成标准**: 运维可按文档演示验收  

---

## 执行顺序

- [x] T1 Agent 类型骨架  
- [x] T2 Chroma 多 collection  
- [x] T3 全局偏好记忆  
- [x] T4 信息检索 Agent（源 B）  
- [x] T5 三分析师  
- [x] T6 风控 Agent  
- [x] T7 协调路由  
- [x] T8 执行确认  
- [x] T9 复盘 Agent  
- [x] T10 Markdown 格式  
- [x] T11 钉钉入口扩展  
- [x] T12 Docker 接入  
- [x] T13 定时/信号钩子  
- [x] T14 E2E smoke  
- [x] T15 文档  

建议：`/exec` 时每完成 T1–T5、T6–T11、T12–T15 各汇报一次。

## 风险与回滚

| 风险 | 缓解 |
|------|------|
| 一期全上范围大 | 任务按竖切可演示；T14 为硬门禁 |
| 2GB ECS + Chroma + 新进程 | compose mem_limit；Agent bot 独立限内存；复用单 Chroma 目录 |
| 固定源无数据/被封 | 失败策略 A：说明失败 + 行情简化结论 |
| 风控「凭经验」误杀 | 输出 `mode=heuristic_v1`；可 `@风控 放行` 覆盖（可选，T6 注明） |
| 确认下单误触 | TTL + 必须「确认」关键字 + 默认先 pending |
| 破坏旧评分 | 默认并存；`AGENT_ORCH_ENABLED=0` 即回滚入口 |

**回滚**：环境变量关闭 Agent 编排；不删 Chroma 数据；旧 `score_feedback` 不动。

## 非目标（本期不做）

- 网页触发 Agent  
- 通用搜索 API Key（A）真实调用  
- 无确认自动下单  
- 关闭旧统一评分入口（验收后另开任务）  

## 建议下一 skill

- 确认本计划后 → **`/exec`**（executing-plans）从 T1 开始  
- 改动面大 → 可先 **`using-git-worktrees`** 隔离分支  
- 实现后 → `/review` → `/security`（钉钉指令注入、下单确认、密钥）→ `/perf`（Chroma/LLM 调用）

# 分析师书籍 RAG + 评分入库 + 24h 复盘反馈学习

> 日期：2026-07-28  
> 来源：brainstorm 冻结（双轨 C；方向对可轻仓；窗口 24h；PDF 分市场 3～5 本；评分入库→24h 复盘→反馈）  
> 建议执行：`/exec` → executing-plans；大改建议先 worktree  

## 背景与目标

在现有自研多 Agent（加密 / 美股 / A 股分析师）上增加：

1. **轨道 A**：分市场 PDF 知识库 RAG，评分时注入书本框架（不替代 K 线/新闻）  
2. **轨道 B**：每次信号评分落库；**+24h** 按涨跌幅复盘；写入反馈记忆，减少误杀、少追高、结构位更有依据  
3. **成功标准**：24h 内**方向正确**即可；建议形态可为 **caution / 轻仓**，不要求满仓高分  

## 验收标准

1. 上传 PDF 后，对应市场分析师评分 Prompt 中可检索到书本片段（可展示书名/章节）  
2. 任意评分通道（Webhook Agent / 钉钉 / 手动）产生记录可查（MySQL 或等价持久化）  
3. 到期任务对 `pending` 记录回填 24h 收益与标签（win / lose / flat）  
4. 「低分/reject 但 24h 方向对」类样本写入 `score_feedback`（或专用 collection），下次同类门禁可放松  
5. 同批历史 A/B（有书 vs 无书）人工抽检 ≥20 份；上线观察一周记录漏报率（reject 后大涨）  

## 非目标

- 不做全书微调 / LoRA  
- 不承诺胜率暴涨  
- 不改实盘下单保证金逻辑（仅评分与建议层）  
- 不在本期强制下线旧 `auto-close` webhook（已共用 adaptive-long）  

## 默认参数（可配置）

| 项 | 默认 |
|----|------|
| 复盘窗口 | 24h |
| 方向正确阈值 | 有利方向收益 ≥ **+1.5%** → `win`；≤ **-1.5%** → `lose`；其余 `flat` |
| 反馈默认动作 | win + 原 reject/低分 → 建议后续 **caution 轻仓**，不直接强制 execute |
| 每市场书籍 | 3～5 本 PDF |
| RAG Top-K | 4 片段，单片段 ≤800 字 |

---

## 架构落点（复用优先）

| 能力 | 复用 | 新建/扩展 |
|------|------|-----------|
| Chroma | `score_feedback_store.py`、`agent_memory_store.py` | collection：`books_crypto` / `books_us` / `books_a_share` |
| 反馈门禁 | `score_feedback.py` | 24h 复盘结果 → `remember_*` / gate patch |
| 分析师 | `agents/analysts/base.py`、`prompts.py` | Prompt 注入书本片段 |
| 定时 | `api/main.py` 已有 `_agent_auto_review_loop` | 新增 `_signal_score_review_24h_loop` |
| 行情回填 | `massive_klines` / HL / crypto klines | `fetch_close_after(symbol, ts, +24h)` |
| ORM | `database/models.py` | 表 `signal_score_events` |

```
PDF 上传 → 解析切片 → Chroma books_*
     │
评分发生 → 写 signal_score_events(pending)
     │         └→ 分析师 Prompt + books RAG + score_feedback
     │
  +24h 定时 → 回填涨跌 → 标签 → score_feedback / agent_reviews
```

---

### T1：评分事件表模型

- **文件**: `backpack_quant_trading/database/models.py`；如需迁移脚本则 `docs/` 或现有 init 惯例旁注 SQL  
- **改动**: 新增表/模型 `SignalScoreEvent`，字段至少：  
  `id`, `created_at`, `review_at`(nullable), `market`, `symbol`, `timeframe`, `action`,  
  `score`, `grade`, `recommendation`, `force_reject`(bool), `entry_price`,  
  `metrics_json`(短), `source`(webhook_agent|dingtalk|manual|…),  
  `status`(pending|reviewed|skipped), `pnl_pct_24h`, `outcome`(win|lose|flat), `review_note`  
- **不做**: 前端大屏（可 P2）  
- **验证**: `python -c "from backpack_quant_trading.database.models import SignalScoreEvent; print(SignalScoreEvent.__tablename__)"`  
- **完成标准**: 模型可导入；字段覆盖入库与复盘  

### T2：评分事件仓储 API

- **文件**: 新建 `backpack_quant_trading/core/signal_score_store.py`  
- **改动**: `save_score_event(...)`、`list_pending_due(now)`、`mark_reviewed(id, pnl, outcome, note)`；失败降级打日志不阻断评分  
- **验证**: 单测或 `python -c` 写入再查出 pending（可用 sqlite/测试库若现网不便）  
- **完成标准**: 评分主路径可调用 `save_score_event` 且异常不影响推送  

### T3：评分出口统一落库

- **文件**: `agents/scheduler_hooks.py`（`run_agent_signal_hook` 成功后）；必要时 `agents/analysts/base.py` / `formatters` 旁路只取 structured  
- **改动**: Agent 评分成功 → `save_score_event`；`review_at = created_at + 24h`  
- **不做**: 旧 `format_dingtalk_message` 海报路径（已停用为主）  
- **验证**: 本地 dry_run 或正式机打测试 webhook 后 DB/日志出现 pending  
- **完成标准**: Webhook Agent 与钉钉点名分析至少一条能入库  

### T4：24h 行情回填工具

- **文件**: 新建 `backpack_quant_trading/core/signal_outcome.py`  
- **改动**: `compute_pnl_pct_24h(market, symbol, action, entry_price, signal_ts) -> float|None`  
  - us → Massive；crypto → 现有 K 线；a_share → 现有 A 股行情源  
  - 多：`(p1-p0)/p0`；空：`(p0-p1)/p0`  
- **验证**: 对已知历史点（如某日 ETH）手算对比误差可接受  
- **完成标准**: 三市场至少 crypto+us 打通；a_share 可先 stub 返回 None→status=skipped  

### T5：到期复盘任务 + 反馈写入

- **文件**: `core/signal_outcome.py` 或 `agents/signal_score_review.py`；`api/main.py` 注册循环；`score_feedback.py`  
- **改动**:  
  - 扫 `status=pending AND review_at<=now`  
  - 算 pnl → outcome（±1.5%）  
  - `outcome=win` 且原 `recommendation in (reject,) or score<52 or force_reject` → 写入反馈 patch（`clear_force_reject` / caution 偏好）  
  - `outcome=lose` 且原 execute/高分 → 收紧追高类反馈  
  - 可选短 markdown 记入 `agent_reviews`  
- **验证**: 造一条 `review_at=过去` 的假数据跑一轮，看 status=reviewed + feedback count+1  
- **完成标准**: 定时循环可开关 `SIGNAL_SCORE_REVIEW_ENABLED=1`；日志有 reviewed=N  

### T6：PDF 入库管道（分市场）

- **文件**: 新建 `backpack_quant_trading/core/book_ingest.py`；`data/books/{crypto,us,a_share}/` + `.gitkeep`；可选 API `api/routers/agent_books.py`  
- **改动**: PDF 文本提取（优先 `pypdf`/`pymupdf`，写入 requirements）；分块；upsert Chroma `books_{market}`；元数据 book/chapter/page  
- **不做**: OCR 扫描版（扫描 PDF 列为后续）  
- **验证**: `python -m ...book_ingest --market crypto --file sample.pdf` 后 count>0  
- **完成标准**: 单市场 1 本 PDF 可入库检索  

### T7：分析师 RAG 注入

- **文件**: `agents/analysts/base.py`（`build_user_prompt`）；`agents/sr_calibrate.py` 旁或新建 `agents/book_rag.py`；`prompts.py` 一句硬约束「可引用书名，勿编造」  
- **改动**: 按 `market` 检索 Top-K；注入「## 书本依据」；structured 可带 `book_citations: []`  
- **验证**: mock/真调用一次，prompt 或卡片含书名  
- **完成标准**: 三分析师路径均按市场隔离检索  

### T8：评分卡展示书本依据（可选但建议）

- **文件**: `agents/formatters.py`  
- **改动**: 若有 `book_citations`，加一小节「📚 书本依据」便于人工抽检  
- **验证**: 格式化 markdown 含书名  
- **完成标准**: 抽检 20 份时可肉眼看到依据  

### T9：管理接口 / 简易脚本

- **文件**: `api/routers/agent_books.py`（上传列表）；或 CLI `tools/ingest_books.py`、`tools/run_signal_score_review.py`  
- **改动**: 运维可上传 PDF、触发复盘扫一次  
- **验证**: curl 或 CLI 成功  
- **完成标准**: 不登录生产容器手改也能完成入库与复盘  

### T10：A/B 与观察清单（文档+脚本）

- **文件**: `docs/plans/` 本文件附录或 `tools/ab_score_compare.py`  
- **改动**: 脚本对历史 N 条：`BOOK_RAG=0/1` 重跑 dry_run，输出分数差；检查清单：一周漏报率  
- **验证**: 对 ≥5 条历史可跑通对比表  
- **完成标准**: 验收步骤可复制执行  

---

## 执行顺序

- [ ] T1 评分事件表模型  
- [ ] T2 评分事件仓储  
- [ ] T3 评分出口落库  
- [ ] T4 24h 行情回填  
- [ ] T5 到期复盘 + 反馈  
- [ ] T6 PDF 入库  
- [ ] T7 分析师 RAG 注入  
- [ ] T8 卡片展示书本依据  
- [ ] T9 管理 CLI/API  
- [ ] T10 A/B 与观察清单  

**推荐并行**：T1–T5（闭环）∥ T6–T8（书籍）；合并顺序先合 T1–T5。  

## 风险与回滚

| 风险 | 缓解 |
|------|------|
| PDF 提取失败/扫描件 | 仅支持文字版；失败明确报错 |
| 24h K 线缺失 | status=skipped，不写错误反馈 |
| 反馈过拟合放宽门禁 | patch 带冷却/置信度；默认只到 caution |
| Chroma/磁盘膨胀 | 分 collection；书籍限 3～5 本/市场 |
| 评分延迟 | RAG/入库异步或超时降级为空书本 |

回滚：`BOOK_RAG_ENABLED=0`、`SIGNAL_SCORE_REVIEW_ENABLED=0` 即关闭新逻辑。  

## 建议下一 skill

- 确认本计划 → **`/exec`（executing-plans）** 从 T1 开始  
- 若担心污染主分支 → 先 **`using-git-worktrees`**  

## 附录：人工抽检 20 份检查项

1. 是否引用书名/章节且不胡扯  
2. 结构位是否仍满足最小距离（已有 sr_calibrate）  
3. 原会 force_reject 的案例，有反馈后是否变为 caution 而非蛮干 execute  
4. 高分追高案例，lose 复盘后是否更谨慎  

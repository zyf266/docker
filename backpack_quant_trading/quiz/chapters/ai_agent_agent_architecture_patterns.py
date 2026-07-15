"""菜鸟教程 - Agent 架构
来源: https://www.runoob.com/ai-agent/agent-architecture.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/agent-architecture.html"

CHAPTER = ChapterSeed(
    slug="agent-architecture",
    title="Agent 架构",
    description="六种主流架构：单 Agent 循环、Plan & Execute、多 Agent、反思、RAG+Agent、DAG 工作流及选型对比。",
    source_url=SOURCE,
    sort_order=10,
    accent="#f59e0b",
    categories=[
        ("基础概念", "Agent 架构定义与核心循环", 1),
        ("单 Agent 循环", "ReAct 与单 Agent Loop", 2),
        ("规划与执行", "Plan & Execute 静态/动态规划", 3),
        ("多 Agent 协作", "Orchestrator 与 Subagent", 4),
        ("反思修正", "Reflection 与 Critic", 5),
        ("RAG+Agent", "检索增强型智能体", 6),
        ("工作流编排", "Workflow / DAG", 7),
        ("选型对比", "横向对比、组合模式与误区", 8),
    ],
    questions=[
        (
            "基础概念", "single",
            "Agent 架构是指什么？",
            "Agent 系统中各组件的组织方式，决定能力边界、可靠性、灵活性和适用场景。",
            [("A", "各组件的组织方式，决定能力与适用场景", True), ("B", "仅指前端 UI 布局", False), ("C", "数据库表结构设计", False), ("D", "GPU 集群拓扑", False)],
        ),
        (
            "基础概念", "single",
            "Agent 的本质工作循环是？",
            "感知 → 推理 → 行动，观察结果后继续循环直到任务完成。",
            [("A", "感知 → 推理 → 行动", True), ("B", "训练 → 部署 → 下线", False), ("C", "输入 → 输出（单次）", False), ("D", "编译 → 链接 → 运行", False)],
        ),
        (
            "基础概念", "true_false",
            "与传统「问一答一」式大模型调用不同，Agent 可连续多步操作、调用工具、协调其他 Agent。",
            "教程明确 Agent 可完成复杂任务，不仅单次问答。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "单 Agent 循环", "single",
            "单 Agent 循环直接体现哪种模式？",
            "单 Agent 循环体现 ReAct（Reasoning + Acting）：每一步先想再做。",
            [("A", "ReAct（Reasoning + Acting）", True), ("B", "仅 Chain-of-Thought", False), ("C", "纯 DAG 工作流", False), ("D", "MapReduce", False)],
        ),
        (
            "单 Agent 循环", "single",
            "单 Agent 循环最主要的瓶颈是？",
            "每次工具调用结果回写上下文，任务推进时上下文不断增长，直至触达窗口限制。",
            [("A", "上下文窗口不断增长直至触顶", True), ("B", "无法调用任何工具", False), ("C", "不支持 Python", False), ("D", "必须联网", False)],
        ),
        (
            "单 Agent 循环", "single",
            "教程建议：任务预计超过多少轮工具调用时，单 Agent 循环可能不是最佳选择？",
            "超过 15 轮工具调用时，考虑多 Agent 或 Plan & Execute 分解复杂度。",
            [("A", "15 轮", True), ("B", "3 轮", False), ("C", "100 轮", False), ("D", "1 轮", False)],
        ),
        (
            "单 Agent 循环", "single",
            "单 Agent 循环的最佳适用场景是？",
            "修复一个 bug、编写一个函数、回答具体问题——任务明确、复杂度适中。",
            [("A", "任务边界清晰的中小任务（修 bug、写函数）", True), ("B", "亿级数据分布式批处理", False), ("C", "多角色并行审查大型 PR", False), ("D", "固定 CI 流水线", False)],
        ),
        (
            "规划与执行", "single",
            "Plan & Execute 架构将工作拆分为哪两个阶段？",
            "先规划（Plan）生成步骤列表，再执行（Execute）依次完成，规划阶段不执行操作。",
            [("A", "先规划（Plan）再执行（Execute）", True), ("B", "先执行再规划", False), ("C", "仅规划不执行", False), ("D", "仅执行不规划", False)],
        ),
        (
            "规划与执行", "single",
            "「静态规划」与「动态规划」的区别是？",
            "静态：计划一次生成、线性执行不调整；动态：每步后根据结果重新评估调整后续计划。",
            [("A", "静态不中途调整，动态每步可重规划", True), ("B", "静态更快但不用 LLM", False), ("C", "动态不能人工审查", False), ("D", "无区别", False)],
        ),
        (
            "规划与执行", "single",
            "Claude Code 的 Plan Mode 体现了哪种架构？",
            "Plan Mode：先输出详细计划供审查，确认后再执行，即 Plan & Execute。",
            [("A", "规划 + 执行（Plan & Execute）", True), ("B", "单 Agent 循环", False), ("C", "纯 DAG 工作流", False), ("D", "仅 RAG 检索", False)],
        ),
        (
            "规划与执行", "true_false",
            "若任务 3 步内可完成，直接用单 Agent 循环通常比 Plan & Execute 更高效。",
            "教程指出简单任务引入两阶段规划反而浪费推理轮次。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "多 Agent 协作", "single",
            "多 Agent 架构中 Orchestrator（协调者）的职责是？",
            "负责任务拆解、调度 Subagent、汇总各子 Agent 结果。",
            [("A", "任务拆解、调度、结果综合", True), ("B", "仅训练模型权重", False), ("C", "仅渲染前端", False), ("D", "管理 DNS", False)],
        ),
        (
            "多 Agent 协作", "single",
            "多 Agent 协作的核心优势之一是？",
            "每个子 Agent 拥有独立上下文窗口，互不干扰，可并行工作。",
            [("A", "子 Agent 独立上下文，可并行", True), ("B", "完全不需要 LLM", False), ("C", "零 Token 成本", False), ("D", "无需协调逻辑", False)],
        ),
        (
            "多 Agent 协作", "single",
            "教程中 Subagent 与 Agent Teams 的区别是？",
            "Subagent 短暂隔离、完成任务即销毁；Agent Teams 是长期协作、互相发消息的团队。",
            [("A", "Subagent 短暂隔离；Teams 长期协作", True), ("B", "完全相同", False), ("C", "Subagent 不能并行", False), ("D", "Teams 没有上下文", False)],
        ),
        (
            "多 Agent 协作", "single",
            "审查 PR 时同时派代码审查、安全检测、性能分析三个子 Agent，属于哪种架构？",
            "Orchestrator 分发任务给专门化 Subagent 并行执行后汇总，即多 Agent 协作。",
            [("A", "多 Agent 协作", True), ("B", "单 Agent 循环", False), ("C", "纯静态 DAG", False), ("D", "仅 RAG", False)],
        ),
        (
            "反思修正", "single",
            "反思架构在 Agent 输出环节加入了什么？",
            "加入质量评估（Critic），不满意则重新生成或修正，形成内部迭代。",
            [("A", "质量评估（Critic）与修正循环", True), ("B", "额外向量数据库", False), ("C", "人工标注平台", False), ("D", "区块链共识", False)],
        ),
        (
            "反思修正", "single",
            "「写单元测试 → 运行测试 → 观察失败 → 修复 → 再运行」对应哪种架构？",
            "测试结果就是 Critic 的反馈信号，是反思架构的经典应用。",
            [("A", "反思与自我修正", True), ("B", "单 Agent 循环", False), ("C", "DAG 工作流", False), ("D", "仅 RAG", False)],
        ),
        (
            "反思修正", "single",
            "Critic 模型相比自我反思的优势是？",
            "独立评判模型更客观，能发现执行模型的盲区；自我反思实现简单但可能视而不见。",
            [("A", "更客观，能发现执行模型盲区", True), ("B", "零成本零延迟", False), ("C", "不需要设置上限", False), ("D", "一定比自我反思差", False)],
        ),
        (
            "反思修正", "true_false",
            "反思循环必须设置最大迭代次数，防止模型陷入「永远不满意」的死循环。",
            "教程明确需设上限，否则可能无限迭代。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "RAG+Agent", "single",
            "RAG + Agent 与普通 RAG 的关键区别是？",
            "普通 RAG 被动固定检索一次；RAG+Agent 由 Agent 自主决定何时检索、检索什么，可多次查询。",
            [("A", "Agent 自主决定何时、检索什么，可多次查询", True), ("B", "RAG+Agent 不用向量库", False), ("C", "普通 RAG 更智能", False), ("D", "无区别", False)],
        ),
        (
            "RAG+Agent", "single",
            "RAG 的价值不仅在于「装得下」大上下文，更在于？",
            "精准检索——减少噪音、降低推理成本、提高答案准确性。",
            [("A", "精准检索，减噪降本提准", True), ("B", "替代所有 Agent 规划", False), ("C", "仅用于图像", False), ("D", "消除幻觉 100%", False)],
        ),
        (
            "RAG+Agent", "single",
            "代码库问答 Agent 被问「为什么这里用单例模式」时，应主动检索什么？",
            "主动检索项目文档、设计决策记录、相关代码，而非仅凭训练记忆猜测。",
            [("A", "文档、设计记录、相关代码", True), ("B", "仅 Wikipedia", False), ("C", "随机网页", False), ("D", "不检索直接猜", False)],
        ),
        (
            "工作流编排", "single",
            "DAG 工作流中「无环（Acyclic）」意味着？",
            "没有无限循环，执行路径可预测，失败节点可单独重试。",
            [("A", "无无限循环，路径可预测、可重试", True), ("B", "必须串行不能并行", False), ("C", "每个节点必须是 LLM", False), ("D", "禁止工具调用", False)],
        ),
        (
            "工作流编排", "single",
            "纯 Agent 与 DAG 工作流相比，DAG 的特点是？",
            "DAG：流程预定义、可预测性高、易调试、框架可重试；纯 Agent 灵活性高但路径不确定。",
            [("A", "流程预定义、可预测性高、易调试重试", True), ("B", "完全自主无预定义", False), ("C", "不能并行", False), ("D", "不需要框架", False)],
        ),
        (
            "工作流编排", "true_false",
            "DAG 定义流程骨架，但每个节点内部仍然可以是 Agent 调用。",
            "教程误区三：工作流编排与 Agent 能力互补，非互斥。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "选型对比", "single",
            "六种架构中「并行能力」最强的是？",
            "多 Agent 协作和 DAG 工作流均支持强并行；对比表中多 Agent 标注并行能力「强」。",
            [("A", "多 Agent 协作 / 工作流编排（DAG）", True), ("B", "单 Agent 循环", False), ("C", "纯反思架构", False), ("D", "仅 CoT", False)],
        ),
        (
            "选型对比", "single",
            "「工作流编排 + 多 Agent」组合的典型场景是？",
            "DAG 定义主流程，每个节点内部是独立 Agent，如 CI 中审查节点、安全扫描节点各是 Agent。",
            [("A", "DAG 主流程，节点内是独立 Agent（如 CI 流水线）", True), ("B", "完全取消编排", False), ("C", "只用一个 Subagent", False), ("D", "禁止并行", False)],
        ),
        (
            "选型对比", "single",
            "「规划执行 + 反思」组合适合什么任务？",
            "先规划再执行，每步后加入反思确保质量，适合对质量要求极高的任务。",
            [("A", "质量要求极高的任务", True), ("B", "3 步内可完成的小修", False), ("C", "纯静态数据迁移脚本", False), ("D", "无需验证的草稿", False)],
        ),
        (
            "选型对比", "single",
            "架构选型第一原则是？",
            "从简单开始，用能满足需求的最简架构；确实需要时才增加复杂度。",
            [("A", "从简单开始，需要时才加复杂度", True), ("B", "永远用最复杂架构", False), ("C", "只看 Token 价格", False), ("D", "禁止组合多种架构", False)],
        ),
        (
            "选型对比", "single",
            "下列哪项是教程指出的常见误区？",
            "误区：架构越复杂越好——若 5 步内单 Agent 可完成，编排开销反而降低效率。",
            [("A", "架构越复杂越好", True), ("B", "应从单 Agent 开始", False), ("C", "DAG 可与 Agent 互补", False), ("D", "RAG 重在精准检索", False)],
        ),
        (
            "选型对比", "single",
            "选择架构时两个核心考量是？",
            "需要多大灵活性应对意外，以及需要多大确定性保证结果可靠。",
            [("A", "灵活性 vs 确定性", True), ("B", "颜色 vs 字体", False), ("C", "CPU vs GPU 品牌", False), ("D", "开源 vs 闭源", False)],
        ),
        (
            "多 Agent 协作", "single",
            "多 Agent 协作的主要缺点是？",
            "协调逻辑复杂难调试、并行 Token 成本更高、Orchestrator 可能成为瓶颈。",
            [("A", "协调复杂、成本高、Orchestrator 可能成瓶颈", True), ("B", "无法并行", False), ("C", "不能有专门角色", False), ("D", "不支持工具调用", False)],
        ),
    ],
)

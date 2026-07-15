"""菜鸟教程 - 推理与规划（Reasoning & Planning）
来源: https://www.runoob.com/ai-agent/reasoning-planning.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/reasoning-planning.html"

CHAPTER = ChapterSeed(
    slug="reasoning-planning",
    title="推理与规划",
    description="CoT、ReAct、Plan-and-Execute、ToT、MCTS、Reflexion 及 SOP、HITL 等工程化实践。",
    source_url=SOURCE,
    sort_order=6,
    accent="#8b5cf6",
    categories=[
        ("基础概念", "推理与规划在 Agent 中的定位与价值", 1),
        ("思维链 CoT", "Chain of Thought 逐步推理", 2),
        ("ReAct 框架", "Reasoning + Acting 交替循环", 3),
        ("Plan-and-Execute", "规划先行、隔离执行", 4),
        ("ToT 与 MCTS", "树状多路径探索与搜索算法", 5),
        ("Reflexion", "自我反思与纠错机制", 6),
        ("工程化实践", "SOP、HITL、RLHF 等混合干预", 7),
        ("框架对比", "各推理规划模式优缺点对比", 8),
    ],
    questions=[
        # 基础概念
        (
            "基础概念", "single",
            "在 AI Agent 架构中，推理与规划（Reasoning & Planning）的主要作用是什么？",
            "推理与规划是将 Agent 从简单问答机升级为自主问题解决者的核心引擎，负责拆解目标、逻辑推演与调度工具。",
            [("A", "将 Agent 从问答机升级为自主问题解决者", True), ("B", "仅负责存储长期记忆", False), ("C", "替代大语言模型进行训练", False), ("D", "只处理图像多模态输入", False)],
        ),
        (
            "基础概念", "single",
            "复杂现实任务往往无法通过什么方式完成？",
            "复杂任务往往无法通过一次生成（One-pass generation）完成，需要拆解、推演与自我修正。",
            [("A", "一次生成（One-pass generation）", True), ("B", "多轮对话", False), ("C", "工具调用", False), ("D", "向量检索", False)],
        ),
        (
            "基础概念", "true_false",
            "推理与规划让 AI 具备拆解目标、逻辑推演、探索路径、自我修正以及调度工具的能力。",
            "教程指出复杂任务需要这些能力，推理与规划正是核心引擎。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # 思维链 CoT
        (
            "思维链 CoT", "single",
            "思维链（Chain of Thought, CoT）的核心思想是什么？",
            "CoT 强制模型在输出最终答案前，先显式输出中间推理步骤（如 Let's think step by step）。",
            [("A", "先显式输出中间推理步骤再给出答案", True), ("B", "直接输出最终答案不加推理", False), ("C", "只调用外部 API 获取答案", False), ("D", "将任务拆给多个 Agent 并行执行", False)],
        ),
        (
            "思维链 CoT", "single",
            "CoT 能显著提升模型表现的原因之一是？",
            "更多 token 代表更多计算量，且后续生成能建立在前面正确的逻辑基础上。",
            [("A", "更多 token 提供计算量，后续可基于正确逻辑生成", True), ("B", "自动访问互联网实时数据", False), ("C", "绕过上下文窗口限制", False), ("D", "完全消除模型幻觉", False)],
        ),
        (
            "思维链 CoT", "single",
            "Few-shot CoT 提示词设计的关键是？",
            "通过提供包含完整推理过程的示例，引导模型按相同方式逐步推理。",
            [("A", "提供含推理过程的示例引导模型逐步推理", True), ("B", "只给最终答案不给过程", False), ("C", "必须使用 XML 标签包裹", False), ("D", "禁止展示任何中间步骤", False)],
        ),
        (
            "思维链 CoT", "single",
            "根据框架对比表，CoT 的主要缺点是？",
            "CoT 实现极简、提升基础推理准确度，但无法调用外部工具，容易一条道走到黑。",
            [("A", "无法调用外部工具，容易一条道走到黑", True), ("B", "计算成本极其高昂", False), ("C", "必须依赖人类审批", False), ("D", "只适合长线复杂任务", False)],
        ),
        # ReAct 框架
        (
            "ReAct 框架", "single",
            "ReAct（Reason + Act）将哪两类能力交织在一起？",
            "ReAct 将内部逻辑推理（Thought）与外部工具交互（Action）交织，形成动态闭环。",
            [("A", "内部推理（Thought）与外部行动（Action）", True), ("B", "图像识别与语音合成", False), ("C", "训练数据与测试数据", False), ("D", "短期记忆与长期记忆", False)],
        ),
        (
            "ReAct 框架", "single",
            "ReAct 范式下 Agent 遵循的循环顺序是？",
            "ReAct 遵循 Thought（思考）→ Action（行动）→ Observation（观察）的循环。",
            [("A", "Thought → Action → Observation", True), ("B", "Action → Observation → Thought", False), ("C", "Observation → Thought → Action → 结束", False), ("D", "Plan → Execute → Review", False)],
        ),
        (
            "ReAct 框架", "single",
            "相比 CoT，ReAct 的主要优势是？",
            "ReAct 让模型睁开眼睛看世界，能通过观测实时调整，动态适应环境。",
            [("A", "动态适应环境，能通过观测实时调整", True), ("B", "Token 消耗呈指数级下降", False), ("C", "完全不需要上下文窗口", False), ("D", "只适合数学计算题", False)],
        ),
        (
            "ReAct 框架", "single",
            "ReAct 在长线任务中的主要局限性是？",
            "思维与动作历史积压在同一个上下文窗口中，任务链过长时易死循环或遗忘初始目标。",
            [("A", "上下文累积导致死循环或遗忘初始目标", True), ("B", "完全无法调用工具", False), ("C", "不能进行任何推理", False), ("D", "必须先由人类制定计划", False)],
        ),
        # Plan-and-Execute
        (
            "Plan-and-Execute", "single",
            "Plan-and-Execute 采用了什么策略？",
            "类似人类做大型项目：先出排期表（规划），再挨个干活（执行）。",
            [("A", "先拆解规划，再按子任务隔离执行", True), ("B", "边想边做不分规划与执行", False), ("C", "只规划不执行", False), ("D", "随机尝试所有可能路径", False)],
        ),
        (
            "Plan-and-Execute", "single",
            "Plan-and-Execute 中 Planner（规划者）的职责是？",
            "Planner 接收大目标，生成详细的 Step-by-Step 子任务列表。",
            [("A", "接收大目标并生成逐步子任务列表", True), ("B", "直接调用所有外部 API", False), ("C", "只负责存储反思记忆", False), ("D", "评估树状搜索各节点得分", False)],
        ),
        (
            "Plan-and-Execute", "single",
            "Plan-and-Execute 中 Executor（执行者）通常是什么？",
            "Executor 按顺序执行子任务，通常是小型的 ReAct Agent，每次只专注当前小目标。",
            [("A", "小型 ReAct Agent，每次专注一个子任务", True), ("B", "专门的人类审核员", False), ("C", "蒙特卡洛树搜索算法", False), ("D", "只做一次性全文生成", False)],
        ),
        (
            "Plan-and-Execute", "single",
            "Plan-and-Execute 的主要缺点是？",
            "极其适合长线复杂任务，但面对突发变化（规划本身出错时）不够灵活。",
            [("A", "规划出错或环境突变时不够灵活", True), ("B", "无法拆解子任务", False), ("C", "上下文始终混乱", False), ("D", "不能用于任何复杂任务", False)],
        ),
        # ToT 与 MCTS
        (
            "ToT 与 MCTS", "single",
            "Tree of Thoughts（ToT）与 CoT 的本质区别是？",
            "CoT 和 Plan-and-Execute 本质上是线性路径；ToT 将推理建模为树，支持多分支探索与回溯。",
            [("A", "ToT 是树状多路径探索，支持评估与回溯", True), ("B", "ToT 只能线性推理", False), ("C", "ToT 不需要任何评估器", False), ("D", "ToT 完全不能用于创意写作", False)],
        ),
        (
            "ToT 与 MCTS", "single",
            "ToT 中 Evaluator（评估器）的作用是什么？",
            "在每个分支点对候选 Thought 打分（如可行、有风险、不可行），决定深入或回溯。",
            [("A", "对候选思维节点打分并决定搜索方向", True), ("B", "只负责最终答案格式化", False), ("C", "替代 LLM 进行训练", False), ("D", "将树结构转为 JSON", False)],
        ),
        (
            "ToT 与 MCTS", "single",
            "MCTS 结合 LLM 时，LLM 可作为什么角色？",
            "LLM 可作为策略网络提供启发式行动建议，也可作为价值网络通过 Rollout 预判成功率。",
            [("A", "策略网络和价值网络", True), ("B", "仅作为数据库存储", False), ("C", "仅作为前端界面", False), ("D", "只负责 Token 分词", False)],
        ),
        (
            "ToT 与 MCTS", "single",
            "ToT / MCTS 模式的主要缺点是？",
            "能解决最高难度复杂逻辑问题，但计算成本极其高昂，Token 消耗呈指数级。",
            [("A", "计算成本高昂，Token 消耗呈指数级", True), ("B", "完全无法回溯错误路径", False), ("C", "不能用于数学或代码任务", False), ("D", "实现比 CoT 更简单", False)],
        ),
        # Reflexion
        (
            "Reflexion", "single",
            "Reflexion 框架赋予 Agent 什么能力？",
            "当输出被判定为失败时，根据反馈生成口语化反思并存入情景记忆，指导下一次尝试。",
            [("A", "基于失败反馈生成反思并自我纠错", True), ("B", "完全禁止重复尝试", False), ("C", "自动删除所有历史记忆", False), ("D", "只依赖人类手动改代码", False)],
        ),
        (
            "Reflexion", "single",
            "Reflexion 闭环中，什么会触发 Reviewer 机制？",
            "当 Agent 输出被判定为失败时触发，例如测试用例未通过、API 报错等。",
            [("A", "输出被判定为失败（如测试未通过、API 报错）", True), ("B", "用户发送第一条消息", False), ("C", "上下文窗口未满", False), ("D", "Planner 生成计划后", False)],
        ),
        (
            "Reflexion", "single",
            "Reflexion 生成的反思（Reflection）通常存入哪里？",
            "反思存入情景记忆（Episodic Memory），作为下一次尝试的上下文提示。",
            [("A", "情景记忆（Episodic Memory）", True), ("B", "模型预训练权重", False), ("C", "向量数据库的永久删除区", False), ("D", "仅打印到日志不保留", False)],
        ),
        (
            "Reflexion", "single",
            "Reflexion 的主要局限是？",
            "具备自我纠错能力，但依赖明确的反馈信号（如编译器报错、测试失败）。",
            [("A", "依赖明确的失败反馈信号", True), ("B", "不能用于代码任务", False), ("C", "必须配合 MCTS 使用", False), ("D", "反思后不能再次尝试", False)],
        ),
        # 工程化实践
        (
            "工程化实践", "single",
            "「子任务模板化（SOP）」的核心做法是？",
            "不让 LLM 自由规划，而是预先定义标准操作程序，让 LLM 在固定状态机中流转。",
            [("A", "预定义 SOP，在固定状态机中流转", True), ("B", "让 LLM 完全自由探索所有路径", False), ("C", "禁止任何人工干预", False), ("D", "只使用 Zero-Shot 不用示例", False)],
        ),
        (
            "工程化实践", "single",
            "HITL（Human-in-the-Loop）典型在哪个环节介入？",
            "Planner 生成任务列表后中断执行，要求人类确认、修改或审批，再交由 Executor 执行。",
            [("A", "Planner 生成计划后、Executor 执行前", True), ("B", "模型预训练阶段", False), ("C", "仅在最终答案展示后", False), ("D", "Token 分词过程中", False)],
        ),
        (
            "工程化实践", "single",
            "HITL 特别适用于以下哪种场景？",
            "高风险操作如删除数据库记录、发送群发邮件、大额资金转账等需要人类审批。",
            [("A", "删除数据库、群发邮件、大额转账等高风险操作", True), ("B", "简单的四则运算", False), ("C", "内部单元测试自动运行", False), ("D", "只读查询公开网页", False)],
        ),
        (
            "工程化实践", "single",
            "RLHF 引导规划主要用于什么阶段？",
            "利用强化学习和人类偏好反馈微调大模型规划能力，多用于底层基座训练阶段（如 o1）。",
            [("A", "底层大语言模型基座的训练阶段", True), ("B", "前端页面样式调整", False), ("C", "Docker 镜像构建", False), ("D", "仅用于 SQLite 数据库迁移", False)],
        ),
        (
            "工程化实践", "true_false",
            "生产级 Agent 开发中，纯靠 LLM 零样本进行复杂规划是稳定可靠的。",
            "教程指出纯靠 LLM 零样本复杂规划不稳定，常用 SOP、HITL 等混合干预策略。",
            [("A", "正确", False), ("B", "错误", True)],
        ),
        # 框架对比
        (
            "框架对比", "single",
            "哪种模式「极其适合长线复杂任务，上下文清晰」？",
            "Plan-and-Execute 先拆解子任务再隔离执行，上下文清晰，适合长线复杂任务。",
            [("A", "Plan-and-Execute", True), ("B", "CoT", False), ("C", "ReAct", False), ("D", "纯 Zero-Shot", False)],
        ),
        (
            "框架对比", "single",
            "哪种模式「实现极简，显著提升基础推理准确度」？",
            "CoT 实现极简，通过逐步推理显著提升数学、逻辑等基础推理准确度。",
            [("A", "CoT", True), ("B", "MCTS", False), ("C", "Reflexion", False), ("D", "HITL", False)],
        ),
        (
            "框架对比", "single",
            "哪种模式「动态适应环境，能通过观测实时调整」？",
            "ReAct 通过 Thought-Action-Observation 循环，能根据外部观测实时调整。",
            [("A", "ReAct", True), ("B", "CoT", False), ("C", "SOP 状态机", False), ("D", "纯 Planner 不执行", False)],
        ),
        (
            "框架对比", "single",
            "哪种模式「具备自我纠错和持续进化的能力」？",
            "Reflexion 基于失败反馈生成反思记忆，具备自我纠错与持续改进能力。",
            [("A", "Reflexion", True), ("B", "CoT", False), ("C", "Plan-and-Execute", False), ("D", "纯 One-pass 生成", False)],
        ),
        (
            "框架对比", "single",
            "面对战略游戏或极高难度推理任务，教程推荐结合什么搜索算法？",
            "业界将 LLM 与 MCTS（蒙特卡洛树搜索）结合，类似 AlphaGo 的核心逻辑。",
            [("A", "MCTS（蒙特卡洛树搜索）", True), ("B", "简单线性 CoT", False), ("C", "仅使用正则表达式", False), ("D", "禁止任何树状搜索", False)],
        ),
        (
            "框架对比", "single",
            "ReAct 与 Plan-and-Execute 解决 ReAct 上下文爆炸的方式有何不同？",
            "Plan-and-Execute 将规划与执行解耦，Executor 每次独立上下文只处理一个子任务。",
            [("A", "解耦规划与执行，子任务使用独立上下文", True), ("B", "完全取消 Observation 步骤", False), ("C", "将所有历史压缩为一条 System 消息", False), ("D", "改用一次性生成不做任何循环", False)],
        ),
    ],
)

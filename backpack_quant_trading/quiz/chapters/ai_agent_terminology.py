"""菜鸟教程 - AI Agent 术语
来源: https://www.runoob.com/ai-agent/ai-terminology.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/ai-terminology.html"

CHAPTER = ChapterSeed(
    slug="ai-agent-terminology",
    title="AI Agent 术语",
    description="编程范式、工程角色、模型底层、Prompt 工程、Agent 架构、Harness、Loop 工具等核心术语。",
    source_url=SOURCE,
    sort_order=2,
    accent="#0ea5e9",
    categories=[
        ("编程范式", "Vibe Coding、Agentic Coding 等新编程范式", 1),
        ("工程角色", "Harness / Loop / Context Engineer 等角色", 2),
        ("模型与底层", "LLM、Token、Embedding、RLHF 等", 3),
        ("Prompt 工程", "Prompt、CoT、ReAct、Few-shot 等", 4),
        ("Agent 架构", "Agent、Multi-Agent、Memory、Agent Loop 等", 5),
        ("Harness 组件", "Harness、MCP、RAG、Skills 等", 6),
        ("Loop 工具", "Workflow、Cron、Human-in-the-loop 等", 7),
        ("工具生态", "Cursor、Claude Code、Copilot 等", 8),
        ("评估与安全", "Eval、Guardrail、Prompt Injection 等", 9),
        ("工程演进", "从 Prompt 到 Loop Engineering 的能力演进", 10),
    ],
    questions=[
        # 编程范式
        (
            "编程范式", "single",
            "「Vibe Coding（氛围编程）」的核心含义是什么？",
            "Vibe Coding 指用自然语言/语音描述需求，让 AI 生成代码，偏随性创作。",
            [("A", "用自然语言描述需求让 AI 生成代码", True), ("B", "严格按 UML 图手写代码", False), ("C", "只做代码审查不写代码", False), ("D", "仅用于数据库建模", False)],
        ),
        (
            "编程范式", "single",
            "「Agentic Coding（智能体编程）」是指什么？",
            "Agentic Coding 强调 Agent 自主完成设计→实现→测试→验收等编程任务。",
            [("A", "Agent 自主完成设计、实现、测试、验收", True), ("B", "只用 Copilot 补全一行代码", False), ("C", "禁止 AI 参与开发", False), ("D", "仅生成 UI 原型", False)],
        ),
        (
            "编程范式", "single",
            "「Context Engineering（上下文工程）」主要解决什么问题？",
            "通过组织上下文、知识、记忆与工具，提升模型在任务中的表现。",
            [("A", "通过组织上下文与知识提升模型效果", True), ("B", "压缩模型参数量", False), ("C", "替换 GPU 硬件", False), ("D", "仅优化前端 CSS", False)],
        ),
        (
            "编程范式", "true_false",
            "「AI Native Development」指默认 AI 参与设计、开发、测试全过程。",
            "AI 原生开发将 AI 作为默认协作方贯穿软件工程全流程。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # 工程角色
        (
            "工程角色", "single",
            "「Harness Engineer（线束工程师）」在教程类比中对应餐厅经营的什么角色？",
            "Harness Engineer 像专业厨师，精通厨具技法，做完自己试味把关。",
            [("A", "专业厨师，精通厨具技法并自行验收", True), ("B", "只负责点菜的顾客", False), ("C", "只写菜单的设计师", False), ("D", "只洗碗的后勤", False)],
        ),
        (
            "工程角色", "single",
            "「Loop Engineer（循环工程师）」主要负责什么？",
            "Loop Engineer 搭建自动化编排系统，统筹排班、采购、出餐节奏等，实现自主进化。",
            [("A", "搭建自动化编排与持续优化系统", True), ("B", "仅训练大模型权重", False), ("C", "只写单次 Prompt", False), ("D", "仅负责 UI 配色", False)],
        ),
        (
            "工程角色", "single",
            "「Agent Operator（智能体运营工程师）」的核心职责是？",
            "持续监控和优化 Agent 执行效果，类似店长优化经营数据。",
            [("A", "持续监控和优化 Agent 执行效果", True), ("B", "设计神经网络结构", False), ("C", "仅采购硬件服务器", False), ("D", "编写操作系统内核", False)],
        ),
        # 模型与底层
        (
            "模型与底层", "single",
            "LLM 的全称是什么？",
            "LLM = Large Language Model（大语言模型）。",
            [("A", "Large Language Model", True), ("B", "Light Learning Machine", False), ("C", "Linear Logic Module", False), ("D", "Local Language Manager", False)],
        ),
        (
            "模型与底层", "single",
            "「Token（词元）」在 LLM 中是什么？",
            "Token 是模型处理文本的最小单位，也是计费和上下文长度的计量单位。",
            [("A", "模型处理文本的最小单位", True), ("B", "数据库主键", False), ("C", "用户登录凭证", False), ("D", "GPU 线程", False)],
        ),
        (
            "模型与底层", "single",
            "「Hallucination（幻觉）」是指？",
            "模型一本正经地编造不存在或与事实、上下文不一致的信息。",
            [("A", "模型编造不存在或与事实不符的信息", True), ("B", "模型响应速度变慢", False), ("C", "上下文窗口扩大", False), ("D", "工具调用成功", False)],
        ),
        (
            "模型与底层", "single",
            "写代码时建议将 Temperature 调低，是因为？",
            "低 Temperature 使采样更稳定、输出更确定，适合代码生成。",
            [("A", "低值输出更稳定、更适合代码", True), ("B", "低值会关闭模型", False), ("C", "低值只能生成图片", False), ("D", "低值增加幻觉", False)],
        ),
        (
            "模型与底层", "single",
            "「Embedding（向量嵌入）」的主要用途是？",
            "把文本/图片转成数字向量，用于相似度计算，是 RAG 的基础。",
            [("A", "将文本转为向量用于相似度计算", True), ("B", "加密数据库密码", False), ("C", "压缩视频文件", False), ("D", "编译 Python 字节码", False)],
        ),
        (
            "模型与底层", "single",
            "「RLHF」的全称与作用是？",
            "Reinforcement Learning from Human Feedback，用人类偏好对齐模型行为。",
            [("A", "基于人类反馈的强化学习，对齐模型行为", True), ("B", "随机语言启发式框架", False), ("C", "快速本地 HTTP 转发", False), ("D", "递归逻辑哈希函数", False)],
        ),
        (
            "模型与底层", "true_false",
            "「Inference（推理）」指模型生成输出的过程，区别于训练（Training）。",
            "训练是学参数，推理是用已训练模型生成结果。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # Prompt 工程
        (
            "Prompt 工程", "single",
            "「Zero-shot（零样本）」是指？",
            "不给示例，直接让模型完成任务。",
            [("A", "不给示例直接完成任务", True), ("B", "给大量标注数据微调", False), ("C", "只生成图片", False), ("D", "必须人工逐步标注每个 token", False)],
        ),
        (
            "Prompt 工程", "single",
            "「Few-shot（少样本）」是指？",
            "给几个示例，引导模型按格式或风格输出。",
            [("A", "给少量示例引导输出格式", True), ("B", "完全不给任何输入", False), ("C", "只用规则引擎", False), ("D", "禁止模型思考", False)],
        ),
        (
            "Prompt 工程", "single",
            "「System Prompt（系统提示词）」的作用是？",
            "定义 Agent 角色、边界、行为的底层指令。",
            [("A", "定义 Agent 角色、边界与行为", True), ("B", "仅记录用户密码", False), ("C", "存储数据库连接串", False), ("D", "替代向量数据库", False)],
        ),
        (
            "Prompt 工程", "single",
            "「Structured Output（结构化输出）」是指？",
            "强制模型按 JSON/XML 等结构化格式输出。",
            [("A", "强制按 JSON/XML 等格式输出", True), ("B", "只允许输出纯图片", False), ("C", "禁止任何标点符号", False), ("D", "必须手写汇编", False)],
        ),
        (
            "Prompt 工程", "single",
            "ReAct 在 Prompt 工程章节中的含义是？",
            "Reasoning + Acting，推理与行动交替进行，是 Agent 核心范式之一。",
            [("A", "Reasoning + Acting，边想边干", True), ("B", "React 前端框架", False), ("C", "仅做批量推理", False), ("D", "递归激活函数", False)],
        ),
        # Agent 架构
        (
            "Agent 架构", "single",
            "教程中「Agent（智能体）」的核心定义是？",
            "能自主感知、决策、执行任务的 AI 程序。",
            [("A", "能自主感知、决策、执行的 AI 程序", True), ("B", "只能回答固定 FAQ 的脚本", False), ("C", "纯静态网页", False), ("D", "数据库索引", False)],
        ),
        (
            "Agent 架构", "single",
            "「Multi-Agent（多智能体）」是指？",
            "多个 Agent 分工协作完成任务。",
            [("A", "多个 Agent 分工协作", True), ("B", "一个模型多种语言", False), ("C", "多个用户共用一个账号", False), ("D", "多核 CPU 并行", False)],
        ),
        (
            "Agent 架构", "single",
            "「Subagent（子智能体）」是指？",
            "主 Agent 派生的专项子 Agent，如专职切配、冷盘。",
            [("A", "主 Agent 派生的专项子 Agent", True), ("B", "模型的子网络层", False), ("C", "用户的子账号", False), ("D", "子目录中的配置文件", False)],
        ),
        (
            "Agent 架构", "single",
            "「Observation（观察）」在 Agent 循环中指？",
            "执行动作后获取反馈信息，用于下一轮思考。",
            [("A", "执行后获取反馈信息", True), ("B", "训练前的数据清洗", False), ("C", "删除历史记忆", False), ("D", "仅指摄像头输入", False)],
        ),
        (
            "Agent 架构", "true_false",
            "「Agent Loop」是思考→行动→观察→再思考的迭代机制。",
            "教程明确 Agent Loop 为持续迭代闭环。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # Harness 组件
        (
            "Harness 组件", "single",
            "「Harness」在 Agent 语境中指？",
            "承载 Agent 执行、上下文管理与工具编排的运行框架，类比整个厨房系统。",
            [("A", "Agent 执行与工具编排的运行框架", True), ("B", "仅指马具", False), ("C", "一种数据库引擎", False), ("D", "前端 CSS 框架", False)],
        ),
        (
            "Harness 组件", "single",
            "「MCP（Model Context Protocol）」是什么？",
            "Agent 连接外部工具/数据源的标准化协议。",
            [("A", "连接外部工具/数据源的标准化协议", True), ("B", "模型压缩算法", False), ("C", "多卡并行训练框架", False), ("D", "消息队列产品", False)],
        ),
        (
            "Harness 组件", "single",
            "「Tool Registry（工具注册中心）」的作用是？",
            "统一管理 Agent 可调用的工具，类比厨房工具架。",
            [("A", "统一管理 Agent 可调用工具", True), ("B", "注册域名 DNS", False), ("C", "Git 分支管理", False), ("D", "用户权限登录", False)],
        ),
        (
            "Harness 组件", "single",
            "教程中「Skills」在 Harness 组件里指？",
            "Agent 可调用的专项能力模块，类比各类烹饪技法。",
            [("A", "Agent 可调用的专项能力模块", True), ("B", "员工软技能培训课程", False), ("C", "操作系统技能认证", False), ("D", "前端动画库", False)],
        ),
        # Loop 工具
        (
            "Loop 工具", "single",
            "「Human-in-the-loop（人在回路）」是指？",
            "关键步骤允许人工干预，如主厨最终确认出餐。",
            [("A", "关键步骤允许人工干预", True), ("B", "完全禁止人类参与", False), ("C", "仅人类手动写代码", False), ("D", "自动删除所有日志", False)],
        ),
        (
            "Loop 工具", "single",
            "「Checkpoint（检查点）」在 Loop 工具中的作用是？",
            "保存执行状态用于恢复，如暂停营业后继续工作。",
            [("A", "保存执行状态以便恢复", True), ("B", "删除全部历史", False), ("C", "强制重启服务器", False), ("D", "仅用于 Git 合并", False)],
        ),
        (
            "Loop 工具", "single",
            "「Cron」在 Loop 工具中指？",
            "按时间计划自动触发的定时任务。",
            [("A", "按时间计划自动触发的定时任务", True), ("B", "一种编程语言", False), ("C", "向量数据库", False), ("D", "模型微调方法", False)],
        ),
        # 工具生态
        (
            "工具生态", "single",
            "教程中将哪个工具描述为「Vibe Coding 主力」AI IDE？",
            "Cursor 被描述为内置 AI 的代码编辑器，Vibe Coding 主力。",
            [("A", "Cursor", True), ("B", "MySQL Workbench", False), ("C", "Photoshop", False), ("D", "Excel", False)],
        ),
        (
            "工具生态", "single",
            "「Claude Code（cc）」属于什么类型？",
            "Anthropic 官方终端 Agent，Harness 的典型代表。",
            [("A", "AI Agent / CLI", True), ("B", "关系型数据库", False), ("C", "静态站点生成器", False), ("D", "区块链钱包", False)],
        ),
        (
            "工具生态", "single",
            "「GitHub Copilot」在早期普及中的定位是？",
            "最早普及的 AI 编程插件，偏辅助补全。",
            [("A", "AI 编程助手，偏辅助补全", True), ("B", "全自主软件工程师", False), ("C", "容器编排平台", False), ("D", "向量检索引擎", False)],
        ),
        # 评估与安全
        (
            "评估与安全", "single",
            "「Prompt Injection（提示词注入）」是指？",
            "恶意输入劫持 AI 行为，如「忽略以上指令」。",
            [("A", "恶意输入劫持 AI 行为", True), ("B", "向数据库注入 SQL", False), ("C", "给模型增加训练数据", False), ("D", "正常编写 System Prompt", False)],
        ),
        (
            "评估与安全", "single",
            "「Guardrail（护栏）」的作用是？",
            "限制 AI 输出范围的安全机制。",
            [("A", "限制 AI 输出范围的安全机制", True), ("B", "加速 GPU 推理", False), ("C", "扩展上下文窗口", False), ("D", "自动生成单元测试", False)],
        ),
        (
            "评估与安全", "single",
            "「Sandbox（沙箱）」在安全语境中指？",
            "隔离执行环境，防止 AI 误操作破坏系统。",
            [("A", "隔离执行环境防止误操作", True), ("B", "公开生产环境", False), ("C", "用户聊天界面", False), ("D", "模型参数存储", False)],
        ),
        (
            "评估与安全", "true_false",
            "「Red Teaming（红队测试）」是主动攻击/诱导 AI 以发现漏洞。",
            "红队测试通过对抗性测试发现安全与对齐问题。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # 工程演进
        (
            "工程演进", "single",
            "AI 工程演进路线中，「Context Engineering」阶段关注什么？",
            "关注给模型什么信息，即上下文组织。",
            [("A", "给什么信息（上下文组织）", True), ("B", "怎么问（提示设计）", False), ("C", "怎么持续自动执行", False), ("D", "仅硬件扩容", False)],
        ),
        (
            "工程演进", "single",
            "「Loop Engineering」阶段的关键能力是？",
            "怎么持续创造结果，即自动执行与反馈闭环。",
            [("A", "持续自动执行与反馈", True), ("B", "仅设计单次 Prompt", False), ("C", "仅手工写代码", False), ("D", "仅部署静态网页", False)],
        ),
        (
            "工程演进", "single",
            "演进路线中「Harness Engineering」关注什么？",
            "怎么组织能力，即工具编排与 Harness 框架。",
            [("A", "怎么组织能力（工具编排）", True), ("B", "怎么问（提示设计）", False), ("C", "仅数据标注", False), ("D", "仅网络布线", False)],
        ),
    ],
)

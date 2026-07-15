"""菜鸟教程 - AI 底层架构
来源: https://www.runoob.com/ai-agent/ai-architecture.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/ai-architecture.html"

CHAPTER = ChapterSeed(
    slug="ai-architecture",
    title="AI 底层架构",
    description="从基础大模型到智能体应用的五层架构、核心名词与完整运行流程。",
    source_url=SOURCE,
    sort_order=3,
    accent="#8b5cf6",
    categories=[
        ("五层架构", "基础层、上下文层、能力扩展层、智能体层、应用层", 1),
        ("核心名词", "Transformer、Token、RAG、MCP、Agent 等", 2),
        ("运行流程", "从用户输入到输出结果的完整链路", 3),
    ],
    questions=[
        # 五层架构
        (
            "五层架构", "single",
            "AI 系统架构中，「基础层（模型）」的核心作用是？",
            "基础层是 AI 的底层计算核心，负责文本理解、Token 预测与语言生成。",
            [("A", "文本理解、Token 预测与语言生成", True), ("B", "封装企业 SaaS 产品", False), ("C", "仅做前端页面渲染", False), ("D", "管理用户登录权限", False)],
        ),
        (
            "五层架构", "single",
            "「上下文层（记忆）」主要负责什么？",
            "管理模型输入上下文，负责短期记忆、长期记忆与外部知识注入。",
            [("A", "管理上下文、记忆与外部知识注入", True), ("B", "训练 Transformer 权重", False), ("C", "编译操作系统内核", False), ("D", "仅执行 SQL 查询", False)],
        ),
        (
            "五层架构", "single",
            "「能力扩展层（工具）」的典型能力不包括？",
            "能力扩展层通过 MCP、Tool Calling、API 等扩展真实世界操作，不包括训练基础模型。",
            [("A", "训练基础大模型权重", True), ("B", "联网搜索", False), ("C", "代码执行", False), ("D", "API 调用", False)],
        ),
        (
            "五层架构", "single",
            "「智能体层（决策）」的核心职责是？",
            "负责目标理解、任务拆解、规划与闭环执行，是 AI 自主决策大脑。",
            [("A", "目标理解、任务拆解、规划与闭环执行", True), ("B", "仅存储向量数据库", False), ("C", "渲染网页界面", False), ("D", "管理 DNS 解析", False)],
        ),
        (
            "五层架构", "single",
            "「应用层（行动）」主要面向什么？",
            "将 Agent 能力封装为可落地产品，如自动化工作流、行业 AI 助手、企业智能系统。",
            [("A", "具体业务场景与可落地产品", True), ("B", "底层矩阵运算", False), ("C", "芯片制程工艺", False), ("D", "网络传输协议", False)],
        ),
        (
            "五层架构", "true_false",
            "上下文层包含 Context Window、Prompt、Memory、RAG 等组件。",
            "教程表格明确列出上下文层的核心组件。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "五层架构", "single",
            "智能体层列出的典型能力包括？",
            "智能体层典型能力：任务规划、多步骤推理、自主决策、闭环执行。",
            [("A", "任务规划、多步骤推理、自主决策、闭环执行", True), ("B", "仅单轮文本补全", False), ("C", "仅图像像素处理", False), ("D", "仅文件系统格式化", False)],
        ),
        # 核心名词
        (
            "核心名词", "single",
            "「Transformer」的核心机制是什么？",
            "Transformer 通过自注意力机制建立 Token 之间的关联关系。",
            [("A", "自注意力机制", True), ("B", "卷积池化", False), ("C", "决策树分裂", False), ("D", "哈希表查找", False)],
        ),
        (
            "核心名词", "single",
            "「Token」在模型中是什么？",
            "Token 是模型处理文本的最小单位，可为子词、单词、字符或符号。",
            [("A", "模型处理文本的最小单位", True), ("B", "用户登录令牌", False), ("C", "数据库连接池", False), ("D", "GPU 驱动版本号", False)],
        ),
        (
            "核心名词", "single",
            "教程中「Prompt」的作用是？",
            "给到模型的输入指令，用来设定角色、控制行为、规范输出格式与目标。",
            [("A", "设定角色、控制行为、规范输出", True), ("B", "仅用于加密通信", False), ("C", "删除历史会话", False), ("D", "压缩模型体积", False)],
        ),
        (
            "核心名词", "single",
            "「RAG」的全称与核心思路是？",
            "Retrieval-Augmented Generation：先检索外部专业知识库，再交由 LLM 整合生成精准答案。",
            [("A", "检索增强生成，先检索再生成", True), ("B", "随机对抗生成", False), ("C", "递归自动梯度", False), ("D", "实时音频网关", False)],
        ),
        (
            "核心名词", "single",
            "「MCP」是指什么？",
            "Model Context Protocol，统一 AI 与工具、数据库、外部服务的通信标准。",
            [("A", "模型上下文协议，统一 AI 与外部服务通信", True), ("B", "多核并行计算框架", False), ("C", "消息压缩协议", False), ("D", "移动客户端平台", False)],
        ),
        (
            "核心名词", "single",
            "教程中「Agent」的定义强调什么能力？",
            "在 LLM 基础上叠加目标+规划+执行能力的自主智能系统。",
            [("A", "目标 + 规划 + 执行的自主智能系统", True), ("B", "仅静态 FAQ 回复", False), ("C", "纯文本编辑器", False), ("D", "关系型数据库", False)],
        ),
        (
            "核心名词", "single",
            "「Tool Calling」是指？",
            "模型主动识别需求、调用外部工具完成实际操作，不局限纯文本回复。",
            [("A", "模型识别需求并调用外部工具执行", True), ("B", "人工手动点击按钮", False), ("C", "仅生成 Markdown 文档", False), ("D", "关闭所有网络连接", False)],
        ),
        (
            "核心名词", "single",
            "「Memory」在架构中解决什么问题？",
            "为 AI 提供短期会话记忆与长期持久记忆，解决上下文遗忘问题。",
            [("A", "短期与长期记忆，解决上下文遗忘", True), ("B", "仅加速 GPU 推理", False), ("C", "替换 Transformer 架构", False), ("D", "管理域名 DNS", False)],
        ),
        (
            "核心名词", "true_false",
            "Tool Calling 让模型可以调用外部工具，不仅限于纯文本回复。",
            "教程核心名词释义明确说明 Tool Calling 可完成实际操作。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        # 运行流程
        (
            "运行流程", "single",
            "Agent 完整运行流程的第一步是？",
            "用户下发指令 Prompt，进入上下文窗口 Context Window。",
            [("A", "用户输入 Prompt 进入上下文窗口", True), ("B", "直接调用数据库备份", False), ("C", "训练新的 LLM 权重", False), ("D", "部署前端静态资源", False)],
        ),
        (
            "运行流程", "single",
            "「记忆增强」阶段会联动哪些能力？",
            "系统联动 Memory 会话记忆 + RAG 外部知识库，补充上下文与专业知识。",
            [("A", "Memory 会话记忆 + RAG 外部知识库", True), ("B", "仅删除全部历史", False), ("C", "仅压缩图片文件", False), ("D", "仅重启服务器", False)],
        ),
        (
            "运行流程", "single",
            "LLM 推理阶段主要通过什么架构进行语义理解？",
            "通过 Transformer 架构对 Token 序列做注意力计算，进行语义理解与初步生成。",
            [("A", "Transformer 对 Token 序列做注意力计算", True), ("B", "纯规则引擎匹配", False), ("C", "手工 if-else 分支", False), ("D", "仅查询本地缓存", False)],
        ),
        (
            "运行流程", "single",
            "「Agent 规划」阶段负责什么？",
            "智能体自主判断、拆解任务，决策是否需要多步骤执行或调用外部工具。",
            [("A", "判断拆解任务，决定是否多步执行或调工具", True), ("B", "仅格式化输出 JSON", False), ("C", "仅记录访问日志", False), ("D", "仅渲染图表", False)],
        ),
        (
            "运行流程", "single",
            "「工具执行」阶段基于什么协议调用外部能力？",
            "基于 MCP 协议，调用 API、数据库、搜索引擎等外部能力完成实操。",
            [("A", "MCP 协议", True), ("B", "FTP 协议", False), ("C", "SMTP 协议", False), ("D", "蓝牙配对协议", False)],
        ),
        (
            "运行流程", "single",
            "流程最后「输出结果」阶段还会做什么？",
            "汇总工具返回与模型推理结果返回用户，同时写入记忆存档。",
            [("A", "返回用户并写入记忆存档", True), ("B", "删除全部上下文", False), ("C", "卸载所有工具", False), ("D", "关闭 MCP 服务", False)],
        ),
        (
            "运行流程", "single",
            "下列哪项是正确的 Agent 完整运行顺序？",
            "用户输入 → 记忆增强 → LLM 推理 → Agent 规划 → 工具执行 → 输出结果。",
            [
                ("A", "输入 → 记忆增强 → LLM推理 → 规划 → 工具执行 → 输出", True),
                ("B", "工具执行 → 输入 → 输出 → 规划", False),
                ("C", "输出 → 输入 → 记忆增强", False),
                ("D", "规划 → 输入 → 删除记忆", False),
            ],
        ),
        (
            "运行流程", "true_false",
            "在完整流程中，Agent 规划发生在 LLM 推理之后、工具执行之前。",
            "教程流程：记忆增强 → LLM推理 → Agent规划 → 工具执行 → 输出。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "五层架构", "single",
            "能力扩展层的核心组件包括？",
            "能力扩展层包含 MCP、Tool Calling、API、Database 等。",
            [("A", "MCP、Tool Calling、API、Database", True), ("B", "仅 HTML 与 CSS", False), ("C", "仅 CPU 与内存", False), ("D", "仅用户界面主题", False)],
        ),
        (
            "核心名词", "single",
            "应用层典型产出不包括？",
            "应用层面向自动化工作流、行业助手、企业智能系统、AI SaaS，不包括训练 Token 化算法本身。",
            [("A", "训练 Token 化底层算法", True), ("B", "自动化工作流", False), ("C", "行业 AI 助手", False), ("D", "企业智能系统", False)],
        ),
    ],
)

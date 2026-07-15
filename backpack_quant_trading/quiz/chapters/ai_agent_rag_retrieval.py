"""菜鸟教程 - RAG 与知识检索
来源: https://www.runoob.com/ai-agent/retrieval-augmented-generation.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/retrieval-augmented-generation.html"

CHAPTER = ChapterSeed(
    slug="rag-retrieval",
    title="RAG 与知识检索",
    description="Naive/Advanced RAG、Chunking、混合检索、Rerank、GraphRAG、RAGAS 评估与数据库选型。",
    source_url=SOURCE,
    sort_order=8,
    accent="#14b8a6",
    categories=[
        ("RAG 基础", "检索增强生成原理与双流水线", 1),
        ("文档切分", "Chunking 策略与重叠", 2),
        ("向量检索", "Embedding 模型与 ANN 算法", 3),
        ("Advanced RAG", "查询优化、混合检索、Rerank", 4),
        ("修正式 RAG", "Self-RAG、CRAG 与 Web 补充", 5),
        ("GraphRAG", "知识图谱与双路检索", 6),
        ("选型与评估", "数据库选型与 RAGAS 指标", 7),
    ],
    questions=[
        (
            "RAG 基础", "single",
            "RAG（Retrieval-Augmented Generation）的核心思想是？",
            "回答前先从外部知识库检索相关内容，再基于检索结果生成，而非仅依赖训练记忆。",
            [("A", "先检索外部知识再生成回答", True), ("B", "只依赖模型预训练权重", False), ("C", "完全不用向量数据库", False), ("D", "仅用于图像生成", False)],
        ),
        (
            "RAG 基础", "single",
            "RAG 主要解决 LLM 的哪两个痛点？",
            "知识截止日期（不知训练后发生的事）和幻觉（不确定时编造答案）。",
            [("A", "知识截止与幻觉", True), ("B", "GPU 显存不足与网络延迟", False), ("C", "前端渲染慢与 CSS 兼容", False), ("D", "数据库连接池耗尽", False)],
        ),
        (
            "RAG 基础", "single",
            "RAG 系统由哪两条流水线组成？",
            "离线索引流水线（文档预处理入库）和在线查询流水线（检索+生成）。",
            [("A", "离线索引 + 在线查询", True), ("B", "训练 + 推理", False), ("C", "前端 + 后端", False), ("D", "上传 + 下载", False)],
        ),
        (
            "RAG 基础", "true_false",
            "在线查询阶段每次用户提问都会经过 Embedding、向量检索、Prompt 拼接和 LLM 生成。",
            "教程流程图：提问→向量化→Top-K 检索→拼接 Prompt→LLM 作答。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "文档切分", "single",
            "文档块太大或太小分别会导致什么问题？",
            "块太大引入噪声，块太小丢失上下文，切分粒度直接影响检索质量。",
            [("A", "太大引入噪声，太小丢失上下文", True), ("B", "只影响存储费用", False), ("C", "与检索无关", False), ("D", "只会加快检索", False)],
        ),
        (
            "文档切分", "single",
            "「递归字符切分」优先按什么边界切分？",
            "RecursiveCharacterTextSplitter 优先按段落、句子等语义边界（\\n\\n、\\n、。等）切分。",
            [("A", "段落、句子等语义边界", True), ("B", "随机位置", False), ("C", "固定每 1 个字符", False), ("D", "仅按文件大小字节", False)],
        ),
        (
            "文档切分", "single",
            "「父子文档检索（Small-to-Big）」的策略是？",
            "用小块高精度检索，命中后返回对应大块（父文档）给 LLM，兼顾精度与上下文。",
            [("A", "小块检索，返回父文档大块", True), ("B", "只存父文档不切块", False), ("C", "删除所有子块", False), ("D", "父块检索子块生成", False)],
        ),
        (
            "文档切分", "single",
            "典型 Chunk 配置中 overlap（重叠）的作用是？",
            "相邻块共享若干字符，防止重要信息在切分边界被截断；常见 512 token 块、50～100 重叠。",
            [("A", "防止边界处重要信息被截断", True), ("B", "增加模型参数量", False), ("C", "替代 Embedding", False), ("D", "加密文档内容", False)],
        ),
        (
            "向量检索", "single",
            "语义相近的文本在向量空间中距离更近，这是什么的数学基础？",
            "Embedding 将文本映射到向量空间，相似度检索基于此。",
            [("A", "相似度检索", True), ("B", "BM25 关键词匹配", False), ("C", "正则表达式", False), ("D", "MD5 哈希", False)],
        ),
        (
            "向量检索", "single",
            "开源且中文效果优秀的 Embedding 模型示例是？",
            "BAAI/bge-m3 等开源模型，中文效果优秀且支持多语言。",
            [("A", "BAAI/bge-m3", True), ("B", "ResNet-50", False), ("C", "Word Count 模型", False), ("D", "SQL 聚合函数", False)],
        ),
        (
            "向量检索", "single",
            "百万级向量毫秒级检索通常采用？",
            "采用近似最近邻 ANN 算法（如 HNSW、IVF），用少量精度换数量级速度提升。",
            [("A", "ANN 算法如 HNSW", True), ("B", "全表暴力扫描", False), ("C", "人工逐条比对", False), ("D", "只检索第一条", False)],
        ),
        (
            "Advanced RAG", "single",
            "HyDE（Hypothetical Document Embedding）的做法是？",
            "让 LLM 先生成假设性答案，用假设答案的向量去检索，往往比原问题召回更好。",
            [("A", "用假设答案的向量检索", True), ("B", "删除用户问题", False), ("C", "禁止使用 LLM", False), ("D", "只检索标题", False)],
        ),
        (
            "Advanced RAG", "single",
            "混合检索（Hybrid Search）结合哪两种方式？",
            "向量检索（懂语义）与 BM25 关键词检索（匹配度高）按权重融合。",
            [("A", "向量检索 + BM25 关键词检索", True), ("B", "CPU 检索 + GPU 检索", False), ("C", "MySQL + Redis", False), ("D", "训练 + 测试", False)],
        ),
        (
            "Advanced RAG", "single",
            "Reranking（重排序）阶段通常使用什么模型？",
            "引入 Cross-Encoder（如 bge-reranker）对「问题-文档」成对精排，从 Top-50 精选 Top-5。",
            [("A", "Cross-Encoder 如 bge-reranker", True), ("B", "纯随机排序", False), ("C", "按文件名字母序", False), ("D", "只用余弦距离不再精排", False)],
        ),
        (
            "Advanced RAG", "single",
            "Advanced RAG 的三段式架构是？",
            "预检索优化 → 检索融合 → 后检索优化（如 Rerank）。",
            [("A", "预检索 → 检索融合 → 后检索", True), ("B", "训练 → 部署 → 下线", False), ("C", "上传 → 压缩 → 删除", False), ("D", "仅 LLM 生成", False)],
        ),
        (
            "修正式 RAG", "single",
            "CRAG（Corrective RAG）在检索质量极低时会？",
            "由 LLM 评判检索结果，质量不足时自动触发 Web Search 等外部补充。",
            [("A", "触发 Web Search 等外部补充", True), ("B", "直接返回空答案", False), ("C", "删除向量库", False), ("D", "停止所有 API", False)],
        ),
        (
            "修正式 RAG", "single",
            "Self-RAG / CRAG 属于什么思路？",
            "加入自我反思机制，对检索结果打分、修正，降低幻觉。",
            [("A", "自我反思与修正式 RAG", True), ("B", "纯暴力检索", False), ("C", "不用检索直接生成", False), ("D", "只用于图像", False)],
        ),
        (
            "GraphRAG", "single",
            "传统 RAG 难以回答哪类问题？",
            "需要跨文档、多跳推理的复杂问题，如多实体关系链查询。",
            [("A", "跨文档多跳推理的复杂问题", True), ("B", "单句翻译", False), ("C", "固定 FAQ 精确匹配", False), ("D", "四则运算", False)],
        ),
        (
            "GraphRAG", "single",
            "GraphRAG 离线阶段从文档提取什么写入图数据库？",
            "使用 LLM 提取三元组（主体、关系、客体）构建知识图谱，如写入 Neo4j。",
            [("A", "三元组（主体、关系、客体）", True), ("B", "仅 MD5 校验和", False), ("C", "用户密码", False), ("D", "CSS 样式表", False)],
        ),
        (
            "GraphRAG", "single",
            "GraphRAG 在线阶段采用什么检索方式？",
            "双路检索：向量检索文档块 + 图检索实体关系子图，再融合给 LLM。",
            [("A", "向量检索 + 图检索双路融合", True), ("B", "只用 SQL LIKE", False), ("C", "只检索图片", False), ("D", "禁止 LLM 参与", False)],
        ),
        (
            "选型与评估", "single",
            "专有名词、产品型号较多的场景，教程首选哪类检索能力？",
            "Weaviate/Elasticsearch 等成熟 BM25 + 向量混合检索，避免向量在专有名词上「翻车」。",
            [("A", "BM25 + 向量混合检索", True), ("B", "只用欧氏距离", False), ("C", "禁用关键词", False), ("D", "纯人工查阅", False)],
        ),
        (
            "选型与评估", "single",
            "RAGAS 框架中 Faithfulness（忠实度）衡量什么？",
            "生成的答案是否都有检索出的文档支撑，是幻觉检测指标。",
            [("A", "答案是否有检索文档支撑", True), ("B", "检索速度毫秒数", False), ("C", "GPU 利用率", False), ("D", "用户点击率", False)],
        ),
        (
            "选型与评估", "single",
            "RAGAS 中 Context Recall 表示？",
            "标准答案中的信息有多少比例能被检索到（检索召回率）。",
            [("A", "标准答案信息被检索到的比例", True), ("B", "LLM 生成 token 数", False), ("C", "文档块平均长度", False), ("D", "API 错误率", False)],
        ),
        (
            "选型与评估", "single",
            "个人知识库、本地开发验证，教程推荐的轻量方案是？",
            "Chroma / FAISS 极轻量，无需独立服务，适合本地开发与个人项目。",
            [("A", "Chroma / FAISS", True), ("B", "十亿级 Milvus 集群", False), ("C", "Oracle RAC", False), ("D", "仅用记事本", False)],
        ),
        (
            "选型与评估", "true_false",
            "Naive RAG 常面临检索不准确、冗余信息多导致「上下文淹没」等问题。",
            "教程指出基础 RAG 的局限，由此引出 Advanced RAG 优化。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "文档切分", "single",
            "语义切分（Semantic Chunking）的依据是？",
            "利用 Embedding 计算相邻句子相似度，在语义转折点自动切分。",
            [("A", "相邻句子 Embedding 相似度找语义转折点", True), ("B", "固定每 10 行切一刀", False), ("C", "按文件修改时间", False), ("D", "随机切分", False)],
        ),
        (
            "RAG 基础", "single",
            "离线索引阶段文档经过 Embedding 后存入哪里？",
            "离线阶段：切分→Embedding→写入向量数据库。",
            [("A", "向量数据库", True), ("B", "关系型事务日志", False), ("C", "浏览器 Cookie", False), ("D", "DNS 缓存", False)],
        ),
    ],
)

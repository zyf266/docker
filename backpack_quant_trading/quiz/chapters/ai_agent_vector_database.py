"""菜鸟教程 - 向量数据库（Vector Database）
来源: https://www.runoob.com/ai-agent/vector-database.html
"""
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

SOURCE = "https://www.runoob.com/ai-agent/vector-database.html"

CHAPTER = ChapterSeed(
    slug="vector-database",
    title="向量数据库",
    description="向量与嵌入、相似度计算、HNSW/IVF 索引、Chroma/Qdrant/pgvector 选型与最佳实践。",
    source_url=SOURCE,
    sort_order=7,
    accent="#06b6d4",
    categories=[
        ("基础概念", "向量数据库定义与传统数据库的区别", 1),
        ("向量与嵌入", "Vector、Embedding 与语义近则向量近", 2),
        ("相似度计算", "余弦相似度、欧氏距离与点积", 3),
        ("索引算法", "Flat、IVF、HNSW 等 ANN 索引", 4),
        ("数据库选型", "Chroma、Qdrant、Milvus、pgvector 等对比", 5),
        ("Chroma 实践", "增删改查与本地嵌入", 6),
        ("应用场景", "RAG、推荐、以图搜图、异常检测等", 7),
        ("最佳实践", "批量插入、归一化、踩坑与优化", 8),
    ],
    questions=[
        (
            "基础概念", "single",
            "向量数据库与传统关系型数据库的核心查询差异是？",
            "传统数据库做精确匹配（WHERE name='Alice'），向量数据库通过相似度找语义相近内容。",
            [("A", "向量库按相似度检索，传统库按精确匹配", True), ("B", "向量库只能存数字，传统库只能存文本", False), ("C", "向量库不支持索引", False), ("D", "传统库不能做全文搜索", False)],
        ),
        (
            "基础概念", "single",
            "用 LIKE '%苹果%' 搜索找不到「iPhone」说明了什么问题？",
            "传统字面匹配无法理解语义，向量数据库通过嵌入实现语义相似检索。",
            [("A", "字面匹配无法理解语义，需要向量语义搜索", True), ("B", "MySQL 不支持模糊查询", False), ("C", "iPhone 不是数据库关键字", False), ("D", "苹果和 iPhone 向量维度不同", False)],
        ),
        (
            "基础概念", "true_false",
            "向量数据库适合「找出和这张图最相似的 10 张图」这类语义相关性检索。",
            "教程将向量库类比为按内容相关性找书，适合图像、语义搜索等场景。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "向量与嵌入", "single",
            "嵌入（Embedding）的核心思想是？",
            "将文本、图片等对象转为向量，语义相近的对象在向量空间中距离更近。",
            [("A", "语义相近的对象，向量空间中距离更近", True), ("B", "把所有对象压缩成相同长度的 JSON", False), ("C", "仅用于加密数据", False), ("D", "替代关系型数据库的主键", False)],
        ),
        (
            "向量与嵌入", "single",
            "机器学习中文本向量维度通常在什么范围？",
            "向量维度通常在 128 到 4096 之间，由嵌入模型决定。",
            [("A", "128～4096 维", True), ("B", "固定 2 维", False), ("C", "1～10 维", False), ("D", "必须等于 1536 维", False)],
        ),
        (
            "向量与嵌入", "single",
            "「向量空间中距离近的两个向量，原始内容语义也更相近」是？",
            "这是向量数据库所有能力的基础：语义近则向量近。",
            [("A", "向量数据库能力的基础原理", True), ("B", "仅适用于英文", False), ("C", "只在二维空间成立", False), ("D", "与嵌入模型无关", False)],
        ),
        (
            "相似度计算", "single",
            "文本语义搜索最常用的相似度方法是？",
            "余弦相似度衡量方向角、忽略长度，是文本场景首选，结果范围 -1 到 1。",
            [("A", "余弦相似度（Cosine Similarity）", True), ("B", "汉明距离", False), ("C", "编辑距离", False), ("D", "Jaccard 系数", False)],
        ),
        (
            "相似度计算", "single",
            "欧氏距离（Euclidean Distance）的结果含义是？",
            "欧氏距离衡量直线距离，值越小越相似，范围 0 到 ∞，适合图像检索等。",
            [("A", "值越小越相似", True), ("B", "值越大越相似", False), ("C", "固定为 1 或 0", False), ("D", "只用于文本", False)],
        ),
        (
            "相似度计算", "single",
            "当向量已归一化时，点积与哪种相似度等价？",
            "向量归一化后，点积等价于余弦相似度，常用于推荐系统。",
            [("A", "余弦相似度", True), ("B", "欧氏距离", False), ("C", "曼哈顿距离", False), ("D", "互信息", False)],
        ),
        (
            "索引算法", "single",
            "暴力检索（Flat）的主要特点是？",
            "遍历所有向量逐一计算，结果 100% 精确，但数据量大时极慢 O(n)。",
            [("A", "100% 精确但数据量大时极慢", True), ("B", "速度最快但完全不精确", False), ("C", "只能用于 HNSW", False), ("D", "不需要向量", False)],
        ),
        (
            "索引算法", "single",
            "IVF 索引的查询思路是？",
            "训练时用 K-Means 聚类，查询时先找最近簇中心，再只在相关簇内精确搜索。",
            [("A", "先聚类找最近簇，再在簇内精确搜索", True), ("B", "随机抽样 1% 向量", False), ("C", "只搜索最新插入的数据", False), ("D", "完全不做近似", False)],
        ),
        (
            "索引算法", "single",
            "HNSW 是目前最主流的向量索引算法，其核心思路是？",
            "构建多层图，查询时从顶层大步跳转定位区域，再逐层细化找最近邻，近似 O(log n)。",
            [("A", "多层图结构，顶层跳转、底层精确搜索", True), ("B", "对所有向量排序后二分", False), ("C", "只用 SQL 索引", False), ("D", "删除 90% 向量加速", False)],
        ),
        (
            "数据库选型", "single",
            "教程建议 AI/LLM 应用原型快速验证优先选？",
            "新手建议从 Chroma 或 pgvector 起步；Chroma 几行代码即可跑通，适合原型。",
            [("A", "Chroma", True), ("B", "Milvus 分布式集群", False), ("C", "自建 Hadoop", False), ("D", "仅用 Excel", False)],
        ),
        (
            "数据库选型", "single",
            "已有 PostgreSQL 且数据量小于 500 万，教程推荐？",
            "已有 PG 环境、数据量 < 500 万时，用 pgvector 无缝集成、零额外运维。",
            [("A", "pgvector 插件", True), ("B", "必须迁移到 Milvus", False), ("C", "只用 Redis", False), ("D", "放弃向量检索", False)],
        ),
        (
            "数据库选型", "single",
            "超大规模（>1 亿向量）且有 K8s 运维能力时，教程推荐？",
            "亿级数据、有 K8s 能力时选 Milvus，分布式、功能全面。",
            [("A", "Milvus", True), ("B", "Chroma 嵌入式", False), ("C", "SQLite", False), ("D", "单机 Flat 暴力检索", False)],
        ),
        (
            "数据库选型", "single",
            "Qdrant 的主要特点是？",
            "Qdrant 用 Rust 实现、性能强劲，适合生产级部署、性能优先场景。",
            [("A", "Rust 实现，生产级性能优先", True), ("B", "仅支持云端 SaaS", False), ("C", "不能过滤元数据", False), ("D", "只存二维向量", False)],
        ),
        (
            "Chroma 实践", "single",
            "Chroma 中 `collection` 类似于关系数据库中的什么？",
            "Collection 类似关系库中的「表」，用于组织同一类向量文档。",
            [("A", "表（Table）", True), ("B", "用户账号", False), ("C", "事务日志", False), ("D", "外键约束", False)],
        ),
        (
            "Chroma 实践", "single",
            "Chroma 设置 `metadata={\"hnsw:space\": \"cosine\"}` 表示？",
            "指定集合使用余弦空间进行相似度计算。",
            [("A", "使用余弦相似度作为距离度量", True), ("B", "禁用 HNSW 索引", False), ("C", "只存 1536 维向量", False), ("D", "自动调用 OpenAI", False)],
        ),
        (
            "Chroma 实践", "single",
            "不想用 OpenAI API 时，教程推荐的本地方案是？",
            "可用 sentence-transformers 本地模型（如 paraphrase-multilingual-MiniLM）完全离线嵌入。",
            [("A", "sentence-transformers 本地嵌入模型", True), ("B", "必须购买 Pinecone", False), ("C", "只能手工写向量", False), ("D", "删除所有 embedding", False)],
        ),
        (
            "应用场景", "single",
            "RAG 系统中向量数据库主要承担哪一步？",
            "在线查询时：问题向量化后在向量库中毫秒级检索最相关文档片段。",
            [("A", "相似度检索 Top-K 文档块", True), ("B", "训练 LLM 权重", False), ("C", "渲染前端页面", False), ("D", "发送钉钉通知", False)],
        ),
        (
            "应用场景", "single",
            "「品味相似的用户喜欢什么」属于向量库的哪类应用？",
            "将用户行为、商品信息转向量做相似用户/物品推荐，是典型推荐场景。",
            [("A", "个性化推荐系统", True), ("B", "区块链挖矿", False), ("C", "DNS 解析", False), ("D", "编译器优化", False)],
        ),
        (
            "应用场景", "single",
            "正常行为聚集、异常向量远离正常区域，对应哪种应用？",
            "异常检测：正常模式聚集，离群向量即异常，如入侵检测、金融欺诈。",
            [("A", "异常检测", True), ("B", "版本控制", False), ("C", "负载均衡", False), ("D", "缓存穿透", False)],
        ),
        (
            "最佳实践", "single",
            "插入和查询必须使用同一个嵌入模型，否则会出现？",
            "嵌入模型不统一会导致维度不匹配或语义空间不一致，检索失效。",
            [("A", "维度不匹配或检索失效", True), ("B", "自动升级索引", False), ("C", "提高准确率", False), ("D", "减少存储空间", False)],
        ),
        (
            "最佳实践", "single",
            "RAG 场景下 `n_results`（top_k）一般建议？",
            "教程建议不要无脑设很大 top_k，RAG 一般 3～10 条足够。",
            [("A", "3～10 条", True), ("B", "至少 1000 条", False), ("C", "固定 1 条", False), ("D", "等于文档总数", False)],
        ),
        (
            "最佳实践", "single",
            "超长文档导致检索相似度不准确，常见解决方案是？",
            "文本过长需先分块（chunking），按段落或固定长度切分，防止语义被稀释。",
            [("A", "文档分块（chunking）", True), ("B", "删除所有标点", False), ("C", "只用英文", False), ("D", "增大 batch size", False)],
        ),
        (
            "最佳实践", "true_false",
            "批量 `collection.add(documents=docs_list)` 比循环单条插入效率更高。",
            "教程明确推荐批量插入，循环单条会反复索引、效率极低。",
            [("A", "正确", True), ("B", "错误", False)],
        ),
        (
            "最佳实践", "single",
            "中文文本本地离线嵌入，教程示例使用的模型是？",
            "示例使用 paraphrase-multilingual-MiniLM-L12-v2，支持中文且可离线。",
            [("A", "paraphrase-multilingual-MiniLM-L12-v2", True), ("B", "GPT-4 权重文件", False), ("C", "ResNet-50", False), ("D", "Word2Vec 1980 版", False)],
        ),
        (
            "最佳实践", "single",
            "pgvector 中 `<=>` 运算符表示？",
            "`<=>` 是 pgvector 的向量距离运算符，用于计算余弦距离。",
            [("A", "向量余弦距离", True), ("B", "字符串拼接", False), ("C", "大于等于比较", False), ("D", "JSON 合并", False)],
        ),
    ],
)

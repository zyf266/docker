# Python 开发常见面试题（本项目适配版）
---

## 一、基础概念

### 1. 可变类型和不可变类型

| 分类 | 类型 |
|------|------|
| 不可变类型 | `int`、`float`、`str`、`tuple` |
| 可变类型 | `list`、`dict`、`set` |

**要点：** 不可变类型的值不能原地修改；可变类型可以原地增删改元素。作为函数默认参数时，可变类型容易引发「共享引用」陷阱。

---

### 2. 深拷贝和浅拷贝的区别

| 方式 | 说明 |
|------|------|
| 浅拷贝 | 只复制最外层对象，内部嵌套元素依旧共享引用 |
| 深拷贝 | 递归复制所有层级对象，完全独立 |

**常用 API：** `copy.copy()`（浅拷贝）、`copy.deepcopy()`（深拷贝）。

---

### 3. `*args` 和 `**kwargs` 的作用

| 语法 | 作用 |
|------|------|
| `*args` | 接收任意数量的位置参数，保存为元组 |
| `**kwargs` | 接收任意数量的关键字参数，保存为字典 |

**典型场景：** 编写通用装饰器、封装第三方 API、路由函数转发参数。

---

### 4. 装饰器

装饰器本质是函数，利用闭包实现，用于在不修改原函数代码的情况下增强其功能（如日志、鉴权、计时、重试）。

```python
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def add(a, b):
    return a + b
```

---

### 5. Python 垃圾回收机制

Python 主要依赖以下机制协同工作：

1. **引用计数**（主要机制）：对象引用数归零时立即回收
2. **标记-清除**（补充）：处理容器对象间的循环引用
3. **分代回收**（优化）：按对象存活时间分代，减少全量扫描开销

---

### 6. 列表推导式和生成器表达式的区别

| 对比项 | 列表推导式 | 生成器表达式 |
|--------|------------|--------------|
| 语法 | `[x for x in iterable]` | `(x for x in iterable)` |
| 求值方式 | 立即生成完整列表 | 惰性求值，按需生成 |
| 内存占用 | 较高 | 极低 |

**选择建议：** 数据量不大时用列表推导式；数据量大且按需消费时用生成器表达式。

---

## 二、并发、性能与框架

### 1. 多线程、多进程、异步 I/O 的区别与选择

| 模型 | 适用场景 | 特点 |
|------|----------|------|
| 多线程 | I/O 密集型 | 同一进程共享内存；CPython 受 GIL 约束，CPU 并行能力有限 |
| 多进程 | CPU 密集型 | 每个进程独立 GIL，可利用多核 CPU |
| 异步 I/O | 高并发 I/O 密集型 | 单线程事件循环 + 非阻塞 I/O，协程切换开销小 |

#### 本项目应用场景

本项目**主要使用多线程 + asyncio 协程**，典型场景包括：

- AI 信号评分（DeepSeek HTTP、钉钉推送）
- 实盘策略运行（每策略独立线程 + 独立事件循环）
- 监控轮询（金十快讯、币安、Polymarket、链上活动等）
- K 线后台同步、研究卡片价格定时刷新

上述任务均为**阻塞型 I/O**（等网络响应），设计目标是「接口快返回、任务慢慢跑」。

#### 本项目并发模型（面试可答）

> 「FastAPI 单进程事件循环 + 守护线程 + 策略线程内独立 asyncio」的混合并发模型。

| 层次 | 实现方式 |
|------|----------|
| API 层 | FastAPI + uvicorn 单 worker |
| 定时调度 | `asyncio.create_task` 启动 K 线同步、盯市、上涨扫描等循环 |
| 阻塞任务隔离 | `asyncio.to_thread()` 将同步重活丢到线程池，不阻塞事件循环 |
| 长驻后台 | `threading.Thread(daemon=True)` 跑监控、评分、扫描 |
| 策略执行 | 每策略一线程，`asyncio.new_event_loop()` + `run_until_complete(strategy.run())` |
| 跨线程投递 | Webhook 用 `asyncio.run_coroutine_threadsafe()` 向策略线程投递信号 |

**并发量级：** 面向个人/小团队量化场景，并发量低；通过锁、防抖、任务互斥和后台化保证稳定性，而非通过多进程/消息队列追求高吞吐。

**未使用：** `multiprocessing`、Redis 任务队列、uvicorn 多 worker 水平扩展。

---

### 2. 协程

协程是一种轻量级的异步编程方式，可在单线程内通过协作式切换实现多个任务的并发执行（非并行）。

**本项目中的协程使用点：**

| 模块 | 用途 |
|------|------|
| `api/main.py` | 定时任务循环（`_kline_sync_loop`、`_daily_a_share_mtm_loop` 等） |
| `strategy/*.py` | 策略 `run()` 内 `await` 行情、下单、`asyncio.sleep` 轮询 |
| `engine/webhook_trading.py` | `aiohttp` 异步 HTTP |
| `core/api_client.py` | 对外 `async def`，内部 `asyncio.to_thread` 包装同步 `requests` |
| `dingtalk_score_bot.py` | dingtalk-stream SDK 要求的 `async def process` 入口 |

---

### 3. GIL 机制

**GIL（Global Interpreter Lock）** 是 CPython 解释器的全局互斥锁，保证同一时刻只有一个线程在执行 Python 字节码。

#### GIL 与 `threading.Lock` 的区别

| | GIL | `threading.Lock` |
|---|-----|------------------|
| 管理者 | 解释器自动管理 | 程序员手动加锁 |
| 保护范围 | Python 字节码执行 | 业务共享数据（dict、JSON 文件、缓存状态） |
| 能否替代 | — | GIL **不能**替代 Lock，两者职责不同 |

#### GIL 何时影响小

线程在等待网络 I/O、`time.sleep()`、部分 C 扩展计算时会释放 GIL，因此本项目大量 I/O 密集线程（评分、监控、同步）**不受 GIL 明显拖累**。

#### 本项目应对措施

| 措施 | 文件示例 | 作用 |
|------|----------|------|
| `threading.Lock` | `dingtalk_signal_cache.py` | 保护最近信号 JSON 缓存 |
| `threading.Lock` | `crypto_signal_scorer.py` | 保护评分缓存与历史记录 |
| `threading.Lock` | `crypto_signal_hub.py` | 扫描任务互斥（`_scan_lock`） |
| `threading.Lock` | `strategy.py` | K 线后台同步防抖（`_bg_sync_lock`） |
| 守护线程 + 快速返回 | `dingtalk_score_bot.py` | 评分不阻塞钉钉回调 |
| 未用多进程 | — | 瓶颈在外部 API 延迟，非本地 CPU |

**面试一句话：** 本项目运行在 CPython GIL 之下，用多线程做 I/O 并发；对共享缓存和任务状态用 `threading.Lock` 保证线程安全；CPU 密集部分未用多进程绕开 GIL，因为当前瓶颈主要在网络延迟。

---

### 4. FastAPI 的核心优势（与 Flask / Django 对比）

| 框架 | 特点 |
|------|------|
| **FastAPI** | 性能高、开发效率快、自动生成 OpenAPI 文档；基于 Starlette（ASGI）+ Pydantic；原生支持 async |
| Flask | 轻量 WSGI 微框架，生态成熟，异步需额外扩展 |
| Django | 全栈 ORM + Admin + 模板，适合大型 Web 应用，相对重量级 |

**本项目选型：** FastAPI 作为量化平台 API 层，挂载 Vue 前端静态资源，注册策略、交易、监控、AI 评分等十余个 Router。

---

### 5. Python 代码性能优化的常见方法

1. 减少循环内重复计算，将不变量提取到循环外
2. 内存优化：大数据用生成器、及时释放大对象、避免无意义的全量缓存
3. CPU 密集型 → 多进程 / C 扩展 / NumPy 向量化
4. I/O 密集型 → 多线程 / asyncio / 连接池
5. 选用高效第三方库（如 `orjson`、`httpx`）
6. 用 `cProfile`、`py-spy`、`line_profiler` 定位热点

**本项目实践：**

- I/O 任务后台线程化（评分、同步、监控）
- `ThreadPoolExecutor` 并发拉取美股周报数据（`us_weekly_report.py`，12 workers）
- K 线同步防抖（300 秒内不重复触发）
- 评分去重缓存，避免重复调用 DeepSeek

---

### 6. 如何排查 Python 项目中的内存泄漏

**常用工具：**

| 工具 | 用途 |
|------|------|
| `memory_profiler` | 逐行/逐函数监控内存增长 |
| `tracemalloc` | 标准库，追踪内存分配栈 |
| `objgraph` | 可视化对象引用关系，定位泄漏对象 |

**常见泄漏原因：**

- 全局列表/字典持续 append 从不清理
- 闭包或回调持有大对象引用
- 线程/定时任务未正确 stop
- ORM Session / 文件句柄未关闭

---

## 三、本项目并发技术对照表（速查）

| 技术 | 是否使用 | 主要场景 |
|------|----------|----------|
| 多线程 `threading` | ✅ | 监控轮询、AI 评分、策略运行、后台同步 |
| 多进程 `multiprocessing` | ❌ | — |
| asyncio 协程 | ✅ | 策略 `run()`、定时调度、`aiohttp` |
| `asyncio.to_thread` | ✅ | 定时任务中跑同步函数 |
| `ThreadPoolExecutor` | ✅ | 美股周报、AI 选股批量 I/O |
| `threading.Lock` | ✅ | JSON 缓存、扫描状态、同步防抖 |
| GIL（CPython 隐式） | ✅ | 所有线程共享；I/O 等待时释放 |
| 高并发架构 | ❌ | 单机小团队，重稳定不重吞吐 |

---

## 四、关键代码路径索引

| 功能 | 文件路径 |
|------|----------|
| API 定时任务启动 | `api/main.py` → `start_kline_scheduler` |
| 策略线程 + 事件循环 | `api/routers/trading.py` → `_run_adaptive_long_in_thread` |
| Webhook 跨线程投递 | `api/main.py` → `run_coroutine_threadsafe` |
| 钉钉手动评分线程 | `dingtalk_score_bot.py` |
| Webhook 自动评分线程 | `core/crypto_signal_scorer.py` → `schedule_webhook_dingtalk_score` |
| 信号缓存锁 | `core/dingtalk_signal_cache.py` |
| K 线后台同步 | `api/routers/strategy.py` → `_schedule_background_sync` |
| 加密扫描互斥 | `api/routers/crypto_signal_hub.py` → `_scan_lock` |

---

*文档版本：2026-07 · 适配沐龙量化交易平台（backpack_quant_trading）*

---

## 五、简历技能栈 × 本项目技术映射（面试开场用）

> 简历来源：`张运繁-Python全栈开发.pdf` · 求职方向 Python 全栈 · 3 年经验

| 简历技能 | 其他项目体现 | 本项目（沐龙量化）体现 | 面试怎么说 |
|----------|--------------|------------------------|------------|
| Python 并发 / GIL | 考试系统高并发、数据流水线 Kafka | 多线程 + asyncio 混合模型 | 见第二章；强调 I/O 密集选型 |
| Django / DRF | 考试系统、邦业业务系统 | **FastAPI**（同类 REST 分层思想） | 「DRF 做 CRUD 与权限；量化台用 FastAPI 追求 async 与 OpenAPI」 |
| Vue3 全家桶 | 考试系统、可视化大屏 | **React 18 + Vite 5**（同类 SPA 工程化） | 「组件化、Router、Axios 联调思路一致，栈是 React」 |
| Pandas 海量清洗 | 同花顺财报、天山质量数据 | 回测、K 线、指标计算、A 股选股 | `strategy.py`、`stock_ai.py`、`pandas-ta` |
| MySQL 调优 / 分库分表 | 考试系统分库分表 + Redis | SQLAlchemy 2 + 策略 K 线表 | `database/models.py`、`strategy_klines` |
| Redis 缓存 | 考试系统题库/成绩热点 | JSON 文件缓存 + 内存 TTL（轻量） | 诚实：本项目用文件锁/JSON；Redis 在考试项目 |
| Kafka / MQTT | 天山数据采集流水线 | 未用 MQ；daemon Thread 解耦 | 「量化台量级不需 MQ；曾用 Kafka 做数据同步」 |
| Docker / Linux | 天山 Docker 流水线 | `start_trading_stack.sh` 三进程部署 | Shell 启停、代理、日志 |
| DeepSeek / 大模型 API | 简历多处 | `crypto_signal_scorer.py` 核心 | Prompt 工程 + 结构化 JSON + 费用治理 |
| WebSocket 行情 | 简历：多交易所 WS | `websockets`/`aiohttp`、HL/Binance REST 轮询 | REST 为主 + 部分 WS 能力 |
| 钉钉 / 企业微信告警 | 简历钉钉；同花顺企微 | 钉钉机器人 + Stream 手动评分 Bot | `tradingview_bot.py`、`dingtalk_score_bot.py` |
| LightGBM / 机器学习 | — | A 股 3–5 日涨跌预测 | `stock_predict_model.py` |
| Web3 / 链上 | — | Ostium、链上活跃度监控 | `web3.py`、`chain_activity_monitor.py` |

**30 秒自我介绍模板：**

> 我有 3 年 Python 全栈经验，做过财报数据引擎、考试系统、工业数据流水线，目前在沐龙独立负责量化交易平台：后端 FastAPI + 前端 React，对接多交易所与 TradingView Webhook，集成 DeepSeek 做信号 AI 评分，用多线程和 asyncio 混合模型保证 7×24 监控与实盘稳定；同时有 MySQL 调优、Docker 部署和 Pandas 大规模清洗的实战经验。

---

## 六、Python 语言深度（高频笔试 & 口述）

### 6.1 面向对象

**Q：Python 的 `__new__` 与 `__init__` 区别？**

- `__new__`：创建实例（类方法），控制「是否创建、创建谁」；元类、单例常用
- `__init__`：初始化已创建实例的属性

**本项目：** `DatabaseManager` 单例、`get_*_instance()` 监控服务单例，保证全局唯一后台线程。

---

**Q：描述符、`@property`、类属性、实例属性区别？**

- 描述符：实现了 `__get__`/`__set__`/`__delete__` 的对象，用于属性访问拦截
- `@property`：只读/可写属性的语法糖

---

**Q：多重继承与 MRO（方法解析顺序）？**

- C3 线性化算法决定 `super()` 调用顺序
- 量化项目策略类继承层次较浅，更多用组合（Engine + Client + Strategy）

---

### 6.2 上下文管理器与异常

**Q：`with` 语句原理？如何自定义？**

- 实现 `__enter__` / `__exit__` 或使用 `@contextmanager`
- **本项目：** SQLAlchemy Session、`threading.Lock`、文件锁 `deepseek_score_usage.lock`

**Q：`try/except/else/finally` 执行顺序？**

- `else` 在无异常时执行；`finally` 必定执行
- 网络请求、交易所下单必须 `finally` 关闭连接/释放锁

---

### 6.3 迭代器、生成器、装饰器进阶

**Q：生成器 `yield` 与协程 `yield from` / `async def` 区别？**

- 生成器：同步惰性迭代
- 协程：事件循环调度，用于 `aiohttp`、策略 `run()` 循环

**Q：类装饰器 vs 函数装饰器？`functools.wraps` 作用？**

- 保留原函数元信息（`__name__`、`__doc__`）
- **本项目：** FastAPI 的 `Depends(require_user)` 类似依赖注入装饰

---

### 6.4 类型与内存

**Q：可变默认参数陷阱？**

```python
def f(a, lst=[]):  # 危险：lst 在函数定义时创建一次
    lst.append(a)
    return lst
```

**Q：`is` 与 `==` 区别？**

- `is` 比较对象身份（id）；`==` 比较值（调用 `__eq__`）

**Q：小整数缓存、字符串驻留？**

- CPython 对 -5~256 整数缓存；面试了解即可

---

## 七、并发编程详解（简历重点 × 本项目）

### 7.1 常问对比题

| 问题 | 标准答法 | 本项目实例 |
|------|----------|------------|
| 什么时候用线程？ | I/O 阻塞、任务需共享内存 | 钉钉评分、快讯轮询 |
| 什么时候用进程？ | CPU 密集、需绕过 GIL | 简历考试压测；本项目 `live_trading` 子进程跑部分交易所 |
| 什么时候用协程？ | 大量 I/O、单线程高并发连接 | FastAPI 调度、`webhook_service` 引擎 |
| 线程池 vs 协程池？ | 阻塞库用 `ThreadPoolExecutor`；原生 async 用 asyncio | `us_weekly_report.py` 12 线程拉 Yahoo |

### 7.2 经典追问

**Q：`asyncio.gather` 与 `create_task` 区别？**

- `gather` 并发等待多个协程完成；`create_task` 调度后台任务不阻塞当前协程
- **本项目：** `api/main.py` startup 用 `create_task` 启动多个定时循环

**Q：`run_coroutine_threadsafe` 使用场景？**

- 从**非协程线程**向**指定事件循环**提交协程
- **本项目：** TradingView Webhook（同步 HTTP）→ 策略线程内的 `execute_signal()`

**Q：死锁四个条件？如何避免？**

- 互斥、占有且等待、不可抢占、循环等待
- **本项目：** 锁粒度小、持锁时间短；K 线同步防抖避免重复抢锁；DeepSeek 文件锁带超时

**Q：守护线程（daemon）是什么？**

- 主线程退出时 daemon 线程被强制结束
- **本项目：** 监控、评分线程均 `daemon=True`，不阻止进程退出

---

## 八、Web 框架（DRF 简历经验 + FastAPI 本项目）

### 8.1 RESTful 设计常问

**Q：REST 核心原则？**

- 资源用 URI 表示；HTTP 方法语义化（GET 查、POST 建、PUT/PATCH 改、DELETE 删）
- 无状态；统一 JSON 响应格式

**Q：PUT 与 PATCH 区别？**

- PUT 全量替换；PATCH 部分更新

**Q：如何设计分页、过滤、排序？**

- `?page=1&page_size=20&sort=-created_at&symbol=BTC`
- **本项目：** 策略交易列表、快讯历史、K 线 limit/offset

---

### 8.2 Django / DRF（简历：考试系统、邦业系统）

**Q：DRF 的 Serializer 作用？**

- 校验入参、序列化出参、嵌套关联、自定义 `validate_*`

**Q：DRF 权限类有哪些？**

- `IsAuthenticated`、`IsAdminUser`、自定义 `BasePermission`

**Q：DRF 分页器？**

- `PageNumberPagination`、`LimitOffsetPagination`、`CursorPagination`（深分页）

**Q：Django ORM N+1 问题？**

- `select_related`（FK 一对一）、`prefetch_related`（M2M 反查）

**Q：分库分表策略？（简历：考试系统）**

- 垂直拆库（用户库/考试库）；水平按 `user_id % N` 或按时间分表
- 中间件路由数据源；分布式 ID（雪花算法）

---

### 8.3 FastAPI（本项目主 API）

**Q：FastAPI 为什么快？**

- Starlette（ASGI）+ Pydantic（C 扩展校验）+ 异步路由

**Q：依赖注入 `Depends` 原理？**

- 声明式解析参数，适合鉴权、DB Session、配置注入
- **本项目：** `require_user` JWT 校验

**Q：`@app.on_event("startup")` 做什么？**

- 启动时注册定时任务、恢复监控线程、补拉缓存

**Q：同步 `def` 路由 vs `async def` 路由？**

- 同步路由在线程池执行，会占 worker；阻塞代码应 `to_thread` 或改 async
- **本项目：** 大量路由为同步 `def` + 内部起后台线程

**Q：FastAPI 与 DRF 对比（面试整合答法）**

| 维度 | DRF | FastAPI（本项目） |
|------|-----|-------------------|
| 协议 | WSGI | ASGI |
| 校验 | Serializer | Pydantic Model |
| 文档 | drf-spectacular 等插件 | 内置 OpenAPI/Swagger |
| 异步 | 3.x 逐步支持 | 原生 async |
| 适用 | 全栈 CRUD、Admin | API 微服务、量化低延迟接口 |

---

## 九、前端（Vue3 简历 × React 本项目）

### 9.1 通用概念（Vue/React 都会问）

**Q：组件化、单向数据流？**

- 父 → 子 props；子 → 父 emit/callback
- **本项目 React：** `views/*.jsx` 页面 + `api/*.js` 请求层

**Q：Vue3 响应式原理？`ref` vs `reactive`？**

- Proxy 劫持；`ref` 包装基本类型，`.value` 访问
- 考试系统简历项目可答

**Q：React 渲染流程？`useState` / `useEffect`？**

- 状态变更 → 重新 render → diff → 更新 DOM
- `useEffect` 处理副作用（拉数据、订阅、定时器）
- **本项目：** `StrategyDetail.jsx` K 线 ECharts、`CurrencyMonitor.jsx` 轮询

**Q：前端性能优化？（简历：懒加载、CDN、压缩）**

- 路由懒加载 `React.lazy` + `Suspense`
- 列表虚拟滚动；ECharts 按需引入
- 生产 `vite build` 分包；FastAPI 托管 `dist` 静态资源

**Q：跨域如何解决？**

- 开发：Vite proxy `/api` → `:8100`
- 生产：同域部署或 CORS 中间件（`api/main.py` 已配置）

**Q：JWT 前端怎么处理？**

- 登录存 `localStorage.token`；Axios 拦截器带 `Authorization: Bearer`
- 401 跳转登录页

---

### 9.2 工程化

**Q：Vite 与 Webpack 区别？**

- Vite 开发用 ES Module 原生服务，冷启动快；生产 Rollup 打包

**Q：Pinia / Vuex vs React 状态管理？**

- 本项目页面级 state 为主，无 Redux；复杂监控池用组件 state + API 轮询

---

## 十、MySQL 与 SQLAlchemy（简历 + 本项目）

### 10.1 MySQL 基础与调优

**Q：InnoDB vs MyISAM？**

- InnoDB：行锁、事务、MVCC、外键；量化订单表必须用 InnoDB

**Q：索引类型？何时失效？**

- B+Tree 聚簇/二级索引；联合索引最左前缀
- 失效：对列函数、`like '%xx'`、类型隐式转换、OR 两侧未建索引

**Q：慢 SQL 排查步骤？**

1. `EXPLAIN` 看 type、key、rows、Extra
2. 加/改索引；改写子查询为 JOIN
3. 拆大查询；读写分离（简历考试系统）

**Q：事务 ACID？隔离级别？**

- 读未提交 / 读已提交 / 可重复读（MySQL 默认）/ 串行化
- 幻读：MVCC + 间隙锁

**Q：分库分表后跨库 JOIN 怎么办？**

- 应用层聚合；宽表冗余；ES 检索（简历项目经验）

---

### 10.2 SQLAlchemy 2.0（本项目）

**Q：ORM 优缺点？**

- 优：模型清晰、防 SQL 注入、迁移方便
- 缺：复杂 SQL 性能、学习成本

**Q：Session 生命周期？**

- `scoped_session` 线程内单 Session；用完 `commit`/`rollback`/`close`

**Q：本项目核心表？**

- `orders`、`positions`、`trades`、`strategy_klines`、`user_instances`、`portfolio_history`

**Q：K 线大量写入如何优化？**

- 批量 `bulk_insert_mappings`；按 symbol+timeframe 去重；增量同步而非全量

---

## 十一、缓存与消息队列（简历 × 本项目对照）

### 11.1 Redis（简历：考试系统）

**Q：Redis 数据类型与应用？**

| 类型 | 场景 |
|------|------|
| String | 缓存、计数器、分布式锁 |
| Hash | 对象字段缓存 |
| List | 消息队列、最新列表 |
| Set | 去重、共同关注 |
| ZSet | 排行榜、延迟队列 |

**Q：缓存穿透、击穿、雪崩？**

| 问题 | 方案 |
|------|------|
| 穿透 | 布隆过滤器、空值缓存 |
| 击穿 | 互斥锁、逻辑过期 |
| 雪崩 | TTL 随机化、多级缓存、熔断 |

**Q：Redis 分布式锁？Redlock？**

- `SET key NX EX` + Lua 释放；Redlock 多节点 quorum

**本项目对照：** 未用 Redis；用 JSON 文件 + `threading.Lock` + 跨进程文件锁做评分去重与日限额——面试可说「量级不大时文件缓存够用；考试系统用 Redis 扛高 QPS」。

---

### 11.2 Kafka / MQTT（简历：天山数据项目）

**Q：Kafka 为什么高吞吐？**

- 顺序写磁盘、零拷贝、分区并行消费、批量发送

**Q：Kafka 如何保证消息不丢？**

- Producer：`acks=all`、重试；Broker 副本；Consumer 手动 commit

**Q：Consumer Group 作用？**

- 同组内分区负载均衡；不同组各自全量消费

**Q：MQTT 与 Kafka 区别？**

- MQTT：轻量 pub/sub，物联网；Kafka：日志型高吞吐流平台

**本项目对照：** 量化台用 **daemon Thread + 钉钉/Webhook** 解耦，未引入 MQ；可答「若信号量上万可引入 Kafka 做评分任务队列」。

---

## 十二、Pandas 与数据处理（简历核心技能）

### 12.1 常问

**Q：`loc` vs `iloc`？**

- `loc` 标签索引；`iloc` 位置索引

**Q：如何处理缺失值？**

- `dropna`、`fillna`、插值；业务规则填充

**Q：`groupby` 原理？**

- Split-Apply-Combine；聚合、转换、过滤

**Q：向量化 vs `apply`？**

- 优先 NumPy/pandas 向量运算；`apply` 慢但灵活

**Q：大 CSV 内存放不下？**

- `chunksize` 分块读取；`dtype` 降级；只读必要列

---

### 12.2 本项目应用

| 场景 | 文件 | 技术点 |
|------|------|--------|
| 策略回测 | `engine/backtest.py`、`strategy.py` | K 线 DataFrame、收益曲线 |
| 技术指标 | `crypto_uptrend_scanner.py` | MACD、EMA、RSI |
| A 股选股 | `stock_ai.py` | akshare 拉取 + 多因子打分 |
| LightGBM 预测 | `stock_predict_model.py` | 特征工程 + `ThreadPoolExecutor` |
| 财报引擎 | 同花顺项目（简历） | 正则 + pandas 清洗 |

---

## 十三、AI / 大模型集成（简历 × 本项目重点）

### 13.1 常问

**Q：如何设计 Prompt？**

- 角色 + 任务 + 输出格式（JSON Schema）+ 约束 + Few-shot 示例
- **本项目：** `_US_STOCK_SYSTEM_PROMPT`、`build_deepseek_user_prompt` 注入 K 线指标 + 新闻

**Q：如何保证 LLM 输出结构化？**

- JSON mode / 明确要求只输出 JSON；后端 `json.loads` + 字段校验 + 默认值兜底

**Q：幻觉如何控制？**

- 只给事实数据（指标数值、新闻标题）；禁止模型编造价格；本地 hard gates 校准分数

**Q：Token 费用如何控制？**

- 短模型（`deepseek-v4-flash`）；关 thinking；缓存去重；日限额文件锁；本机默认关加密评分

**Q：RAG 了解吗？本项目是否用 RAG？**

- 检索增强生成：向量库 + 片段注入 Prompt
- **本项目：** 非完整 RAG；用「实时新闻摘要 + K 线快照」拼进 Prompt，属轻量 Context 注入

---

### 13.2 本项目 AI 评分流水线（必背）

```
TradingView / 手动钉钉 @评分
  → signal_asset_router 分流（crypto / us_stock / a_share）
  → 拉 K 线（Hyperliquid / Massive）+ 新闻上下文
  → 本地指标 hard gates（大周期死叉 → force_reject）
  → DeepSeek 结构化 JSON（score/grade/recommendation/summary）
  → calibrate 校准（分数与摘要对齐 harmonize_summary_score）
  → 钉钉 Markdown 推送
```

**旁路架构：** 评分在 daemon Thread，不阻塞 Webhook 下单（adaptive-long 可选同步评分再开仓）。

---

## 十四、量化交易 & 实时行情（简历 × 本项目）

### 14.1 基础概念

**Q：K 线 OHLCV 含义？**

- Open/High/Low/Close/Volume；周期 1m/5m/1h/4h/1d

**Q：市价单 vs 限价单？**

- 市价：立即成交滑点；限价：指定价格可能不成交

**Q：永续合约资金费率？**

- 多空平衡机制；量化策略需考虑持仓成本

**Q：回测过拟合如何避免？**

- 样本外验证；减少参数；滑点手续费；前视偏差禁止

---

### 14.2 WebSocket vs REST（简历常写 WS）

**Q：WebSocket 与 HTTP 长轮询区别？**

- WS：全双工、低延迟、服务端推送
- 长轮询：反复 HTTP 请求，延迟高

**Q：WS 断线重连策略？**

- 心跳 ping/pong；指数退避重连；快照 + 增量合并

**本项目：**

- `requirements.txt` 含 `websockets`；Binance/HL 多处 **REST 轮询** + 定时拉 K 线
- 面试答法：「架构上支持 WS；当前监控以 REST + 后台线程为主，满足分钟级/秒级告警」

---

### 14.3 本项目交易架构

**Q：TradingView Webhook 流程？**

```
TV Alert → webhook_service :8005（HMAC 验签）
  → 路由到策略实例（instance_id / strategy_name）
  → asyncio.Lock 防并发重复下单
  → Ostium/HL/Backpack API 下单
  → MySQL 落库 orders/trades
  → 可选：Thread 触发 AI 评分 → 钉钉
```

**Q：为什么三进程部署？**

| 进程 | 端口 | 原因 |
|------|------|------|
| `run_api.py` | 8100 | 主平台 + 前端 + 调度 |
| `webhook_service.py` | 8005 | 交易低延迟，独立重启 |
| `tradingview_bot.py` | 5001 | 钉钉多群路由，与 API 解耦 |

**Q：支持哪些交易所？**

- Hyperliquid、Binance、Backpack、Deepcoin、Ostium（Arbitrum）、Lighter、OKX（CLI）

---

## 十五、安全、认证与运维（简历技能）

### 15.1 安全常问

**Q：JWT 组成？如何防篡改？**

- Header.Payload.Signature；HMAC 或 RSA 签名；服务端密钥校验

**Q：密码如何存储？**

-  bcrypt/argon2 哈希 + 盐；本项目 `passlib[bcrypt]`

**Q：Webhook 如何防伪造？**

- HMAC-SHA256 签名 + 时间戳防重放

**Q：API Key 如何管理？**

- `.env` 环境变量；不入 Git；不入 MySQL 明文

---

### 15.2 Docker / Linux / Git（简历）

**Q：Docker 镜像与容器区别？**

- 镜像是只读模板；容器是运行实例

**Q：`Dockerfile` 常见指令？**

- `FROM`、`COPY`、`RUN`、`CMD`、`EXPOSE`、`ENV`

**Q：Docker Compose 作用？**

- 多容器编排；本项目可用 Compose 起 API + MySQL + 代理

**Q：Git 冲突如何解决？**

- `pull` → 手动 merge → `add` → `commit`；或 `rebase` 保持线性历史

**Q：GitFlow 分支模型？**

- `main` 生产、`develop` 开发、`feature/*` 功能、`hotfix/*` 紧急修复

**Q：Linux 排查线上 CPU 高？**

- `top`/`htop` → `py-spy`/`strace` → 查日志 → 限流/扩容

---

## 十六、监控告警模块（本项目特色 · 面试亮点）

### 16.1 模块一览

| 模块 | 技术 | 并发 |
|------|------|------|
| 自选快讯 | 金十/东财/雅虎 RSS | daemon Thread 30s |
| 币安分钟预警 | Binance REST K 线+深度 | daemon Thread |
| 链上活跃度 | Web3 JSON-RPC | daemon Thread |
| MACD 形态 | Binance + ta 库 | daemon Thread |
| Polymarket | Gamma/CLOB API | daemon Thread |
| 钉钉手动评分 | dingtalk-stream | Thread 评分 |

### 16.2 常问

**Q：监控服务重启如何恢复？**

- 配置持久化 JSON/MySQL；`try_restore_from_disk()`；`user_stopped` 标志防误启

**Q：如何避免重复告警？**

- 冷却时间；同一事件 dedupe key；推送历史 JSON

**Q：钉钉机器人安全设置？**

- 自定义关键词「提醒」；IP 白名单；签名校验

---

## 十七、系统设计题（结合简历项目）

### 17.1 考试系统（简历：新天山）

**Q：如何支撑万人同时在线考试？**

- 读多写少：Redis 缓存题库；CDN 静态资源
- 写：分库分表存答卷；异步批改入 Kafka
- 接口：限流、熔断；压测找瓶颈

**Q：如何防止作弊？**

- 切屏检测、试题乱序、选项乱序、倒计时服务端校验

---

### 17.2 数据流水线（简历：天山质量）

**Q：传感器数据海量入库方案？**

- 边缘粗清洗 → Kafka 缓冲 → 消费者细清洗 → MySQL 分区表
- 配置驱动规则引擎（YAML/JSON 定义字段映射）

---

### 17.3 量化平台（本项目）

**Q：如果信号量从每天 10 条涨到 1 万条，如何改造？**

- 评分任务入 Redis/Kafka 队列；Worker 池消费
- DeepSeek 批量 + 更激进缓存；读写分离
- Webhook 与评分彻底拆微服务 + 水平扩展

**Q：如何保证下单不重不漏？**

- `asyncio.Lock`  per 实例；幂等键（signal_id）；先查持仓再下单

---

## 十八、算法与数据结构（笔试常见）

> 简历数据科学背景，基础题仍可能考

| 类别 | 常考 | 准备建议 |
|------|------|----------|
| 数组 | 两数之和、滑动窗口、双指针 | LeetCode Easy/Medium |
| 链表 | 反转、环检测、合并 | |
| 树 | 层序遍历、BST 验证 | |
| 哈希 | 两数之和、字母异位词 | |
| 排序 | 快排 O(nlogn)、堆 TopK | |
| 动态规划 | 爬楼梯、股票买卖 | 量化相关可提 |

**结合项目：**

- TopK 上涨币扫描：小顶堆 / `nlargest`
- 信号去重：哈希 set + TTL

---

## 十九、软技能与行为面试（STAR 法则）

### 19.1 常见问题与答题方向

**Q：介绍最有挑战的项目？**

> **S** 独立搭建沐龙量化全栈台，多交易所 + AI 评分 + 7×24 监控  
> **T** 保证 Webhook 低延迟同时跑重 AI 分析  
> **A** 三进程拆分、评分旁路 Thread、文件锁控 DeepSeek 费用、混合并发模型  
> **R** 实盘稳定运行，信号评分钉钉闭环

**Q：与同事意见不合怎么办？**

- 数据/压测说话；小范围试点；尊重最终决策

**Q：如何快速学习新技术？**

- 官方文档 + 小 Demo + 接入现有项目；AI 辅助读源码

**Q：为什么离开上一家公司？**

- 个人发展、城市（杭州）、技术深度等（按真实原因准备）

---

## 二十、快速自测清单（面试前 1 小时过一遍）

### Python
- [ ] GIL 是什么？何时释放？
- [ ] 深/浅拷贝；装饰器；生成器
- [ ] `*args` / `**kwargs`

### 并发
- [ ] 线程 / 进程 / 协程选型
- [ ] `asyncio.to_thread`、`run_coroutine_threadsafe`
- [ ] 死锁与 `Lock`

### Web
- [ ] RESTful 语义；JWT 流程
- [ ] FastAPI vs DRF 区别
- [ ] 跨域 CORS

### 数据库
- [ ] 索引最左前缀；EXPLAIN
- [ ] 事务隔离级别
- [ ] 分库分表（考试项目）

### 缓存/MQ
- [ ] Redis 五类型；穿透/击穿/雪崩
- [ ] Kafka 分区与消费者组

### 本项目必背
- [ ] 三进程部署原因
- [ ] AI 评分流水线 6 步
- [ ] 旁路架构 vs 同步评分开仓
- [ ] 钉钉回复评分品种识别逻辑
- [ ] DeepSeek 费用控制手段

### 数据处理
- [ ] Pandas 向量化；大文件分块
- [ ] LightGBM 训练流程（A 股选股）

---

## 二十一、关键代码路径索引（扩展版）

| 功能 | 文件路径 |
|------|----------|
| FastAPI 入口 | `run_api.py` |
| 路由注册 | `api/main.py` |
| JWT 认证 | `api/routers/auth.py` |
| 实盘策略启停 | `api/routers/trading.py` |
| Webhook 微服务 | `webhook_service.py` |
| TV 钉钉 Bot | `tradingview_bot.py` |
| 手动评分 Bot | `dingtalk_score_bot.py` |
| 加密 AI 评分 | `core/crypto_signal_scorer.py` |
| 美股 AI 评分 | `core/us_stock_signal_scorer.py` |
| 资产路由 | `core/signal_asset_router.py` |
| 信号缓存 | `core/dingtalk_signal_cache.py` |
| 手动评分解析 | `core/dingtalk_manual_score.py` |
| 快讯监控 | `core/stock_news_alert.py` |
| 币安监控 | `core/binance_monitor.py` |
| 链上监控 | `core/chain_activity_monitor.py` |
| K 线 Massive | `core/massive_klines.py` |
| A 股选股 | `core/stock_ai.py` |
| 数据库模型 | `database/models.py` |
| 前端策略详情 | `frontend/src/views/StrategyDetail.jsx` |
| 生产启动脚本 | `tools/start_trading_stack.sh` |
| 架构面试文档 | `docs/系统架构与功能介绍-面试版.md` |

---

## 二十二、模拟面试 20 道必答题 + 标准答案

> 覆盖：自我介绍、量化项目、并发、数据库、AI、系统设计、简历其他项目。建议**先自己答一遍**，再对照标准答案查漏补缺。

---

### 第 1 题：请用 1～2 分钟介绍一下你自己

**标准答案：**

我叫张运繁，本科数据科学与大数据技术，有 3 年 Python 开发经验。早期在同花顺做港股财报自动化清洗和 MySQL 数据监控；之后在邦业科技负责 Docker 数据流水线和 Pandas 分层清洗；近期在沐龙实业独立搭建量化交易全栈平台，后端用 FastAPI、前端 React，对接 TradingView Webhook 和多交易所实盘，并集成 DeepSeek 做信号 AI 评分和钉钉告警。熟悉 Python 并发、Pandas 数据处理、MySQL 调优，也有 DRF+Vue3 考试系统从 0 到 1 的全栈经验。希望能在杭州继续做 Python 全栈或后端开发，把数据处理和工程化能力结合起来。

---

### 第 2 题：介绍你最有代表性的项目——量化交易后台

**标准答案：**

这是我在沐龙**独立负责**的全栈项目，服务内部实盘，覆盖加密、美股、A 股多市场。

**架构上**拆成三个进程：`run_api.py`（8100）主平台和前端；`webhook_service.py`（8005）专接 TradingView 低延迟下单；`tradingview_bot.py`（5001）解析信号并路由到不同钉钉群。拆进程是为了交易路径不被 AI 评分、快讯轮询等重任务抢 GIL。

**核心模块：**
1. **实盘交易**：支持 Hyperliquid、Binance、Backpack、Ostium 等，Webhook 驱动策略实例，每策略独立线程 + asyncio 事件循环。
2. **AI 信号评分**：拉 K 线算本地指标 → 拼 Prompt 调 DeepSeek → 本地 hard gates 校准 → 钉钉推送评分卡。
3. **监控告警**：快讯、币安分钟异动、链上活跃度、MACD 形态等，均为 daemon 线程轮询。
4. **前端**：React + ECharts 展示策略矩阵、K 线、持仓和监控池。

**难点**：保证 Webhook 毫秒级响应的同时跑 AI 分析——采用**旁路架构**，评分放后台线程，不阻塞下单；DeepSeek 用跨进程文件锁做日限额和 120 秒去重，控制费用。

---

### 第 3 题：你们为什么用 FastAPI 而不是 Django/DRF？

**标准答案：**

我其他项目（考试系统、邦业业务系统）用 **DRF**，擅长 Serializer、权限和 Admin 快速搭 CRUD。量化平台选型 **FastAPI** 主要考虑：

1. **异步原生**：ASGI + `asyncio`，适合定时调度、Webhook 引擎、aiohttp 下单。
2. **性能与文档**：Pydantic 校验快，自带 OpenAPI，前后端联调效率高。
3. **轻量**：不需要 Django Admin/模板，主要是 API + 静态前端。
4. **类型提示**：接口入参出参清晰，维护 2100+ 行的 `strategy.py` 时更安全。

如果面试官问「你会不会 Django」——会，考试系统做过分库分表 + Redis 缓存 + 高并发组卷，和 FastAPI 只是框架不同，**REST 分层、鉴权、ORM 思想是相通的**。

---

### 第 4 题：说说你们项目的并发模型？为什么不用 Kafka？

**标准答案：**

我们用的是 **「FastAPI 单进程事件循环 + 守护线程 + 策略线程内独立 asyncio」** 混合模型：

| 场景 | 方案 |
|------|------|
| HTTP API | Uvicorn 事件循环 |
| 定时任务（K 线同步、盯市） | `asyncio.create_task` + `asyncio.to_thread` 跑同步函数 |
| 监控轮询、AI 评分 | `threading.Thread(daemon=True)` |
| 策略主循环 | 每策略一线程，`new_event_loop()` + `run_until_complete` |
| Webhook 投递信号 | `run_coroutine_threadsafe` 跨线程 |

**不用 Kafka 的原因**：当前是**小团队、低 QPS**——每天信号几十～几百条，daemon 线程 + 快速返回足够。线程间用 `threading.Lock` 和 JSON 文件锁保证缓存安全。

**我在天山数据项目用过 Kafka**：传感器数据削峰、异步消费入库。若量化信号涨到上万条/天，我会把 AI 评分改成 **Kafka 队列 + Worker 池**，Webhook 只发消息不等待评分。

---

### 第 5 题：什么是 GIL？对你们项目有什么影响？

**标准答案：**

GIL 是 CPython 的全局互斥锁，同一时刻只有一个线程执行 Python 字节码。等网络 I/O、`sleep`、部分 C 扩展时会释放 GIL。

**对我们影响小**，因为瓶颈在：
- DeepSeek HTTP 等待
- 交易所/Binance/Yahoo API 等待
- 钉钉推送等待

这些场景多线程仍然有效。

**GIL 不能替代 `threading.Lock`**：我们写 JSON 缓存（信号缓存、评分历史）必须手动加锁，否则两个线程可能写坏文件。

CPU 密集若成为瓶颈（如大批量 LightGBM），可用多进程或线程池 + NumPy C 实现；当前未上多进程绕 GIL，因为**延迟主要在外部 API**。

---

### 第 6 题：AI 信号评分完整流程是什么？如何保证分数可信？

**标准答案：**

**流程（6 步）：**
1. 信号进入（TradingView Webhook / 钉钉手动 @评分）
2. `signal_asset_router` 按品种分流：加密 / 美股 / A 股
3. 拉 K 线（Hyperliquid 或 Massive/Polygon）+ 新闻上下文
4. 本地算 MACD、EMA、RSI 等，跑 **hard gates**（大周期死叉可 force_reject）
5. 调 DeepSeek，要求返回结构化 JSON：`score`、`grade`、`recommendation`、`summary`
6. **本地校准**：公式锚定分 + `harmonize_summary_score` 让摘要分数与展示分一致 → 钉钉 Markdown 推送

**可信性保障：**
- Prompt 只注入真实指标和新闻，要求模型不编造价格
- 本地 gates 可否决模型「建议执行」
- 120 秒同品种同方向去重，避免重复调用
- 跨进程文件锁限制日调用量，防止费用失控

---

### 第 7 题：DeepSeek 费用如何控制？（结合代码说）

**标准答案：**

1. **模型选型**：默认 `deepseek-v4-flash`，关闭 thinking（`DEEPSEEK_SCORE_THINKING=0`）
2. **开关**：本机开发默认 `CRYPTO_SCORE_ENABLED=0`；服务器用 `TRADING_SERVER=1` 控制
3. **去重缓存**：120 秒内相同 symbol+action+周期，只推送缓存不重复调 API
4. **跨进程文件锁**：`deepseek_score_usage.lock` + `deepseek_score_usage.json`，`run_api`、`tradingview_bot`、`dingtalk_score_bot` 共享日配额
5. **旁路异步**：评分失败不影响下单
6. **审计**：`usage.json` 记录 host、pid、模型，便于排查异常调用

---

### 第 8 题：TradingView Webhook 到实盘下单的链路？如何防止重复下单？

**标准答案：**

```
TradingView Alert JSON
  → webhook_service :8005
  → HMAC-SHA256 签名校验（防伪造）
  → 按 instance_id / strategy_name 路由到策略实例
  → 该实例 asyncio 事件循环内 execute_signal()
  → asyncio.Lock 防止并发信号重复下单
  → 查当前持仓 → 调 Ostium/HL/Backpack API
  → MySQL 写入 orders / trades / positions
  → 可选：daemon Thread 触发 AI 评分
```

**防重复：**
- 实例级 `asyncio.Lock`
- 信号逻辑判断：已有同向持仓则忽略开仓
- adaptive-long 可配置「评分未达标不开仓」

---

### 第 9 题：MySQL 慢 SQL 你怎么排查和优化？（结合项目经验）

**标准答案：**

**排查步骤：**
1. 开启慢查询日志或用 `EXPLAIN` 看执行计划
2. 关注 `type`（是否 ALL 全表扫描）、`key`（是否走索引）、`rows`（扫描行数）
3. 用 `show profile` 或监控看耗时分布

**优化手段：**
- 建联合索引（最左前缀），如 `strategy_klines(symbol, timeframe, open_time)`
- 避免 `SELECT *`，只查必要列
- 批量插入 K 线，增量同步代替全量
- 大分页改游标分页

**简历补充（考试系统）：** 题库/成绩热点数据放 Redis；答卷表按考试 ID 分表；压测后给高频查询加索引，接口 P99 从 xxx ms 降到 xxx ms（按实际填数字）。

---

### 第 10 题：Redis 缓存穿透、击穿、雪崩分别是什么？你怎么解决？

**标准答案：**

| 问题 | 含义 | 方案 |
|------|------|------|
| **穿透** | 查不存在的数据，缓存和 DB 都没有 | 布隆过滤器；空值缓存短 TTL |
| **击穿** | 热点 key 过期瞬间大量请求打到 DB | 互斥锁重建；逻辑过期（异步刷新） |
| **雪崩** | 大量 key 同时过期或 Redis 宕机 | TTL 加随机值；多级缓存；熔断降级 |

**考试系统项目**：题库 ID 列表缓存 Redis，未命中再查 MySQL；开考前预热缓存。

**量化本项目**：未用 Redis，用 JSON 文件 + 内存 TTL（如美股周报 5 分钟缓存）；量级小够用。面试可主动说明差异，体现**按场景选型**。

---

### 第 11 题：分库分表你怎么设计的？（考试系统项目）

**标准答案：**

**垂直拆分**：用户库、考试业务库、日志库，按业务边界隔离。

**水平拆分（答卷表）**：按 `exam_id` 或 `user_id % 16` 分表，单表控制在百万行以内。

**路由**：应用层根据分片键算表名；或中间件（ShardingSphere）。

**带来的问题：**
- 跨分片 JOIN 困难 → 宽表冗余、应用层聚合
- 分布式 ID → 雪花算法
- 扩容 → 双倍扩容迁移方案

**配合 Redis**：缓存试题、考试配置等读多写少数据，减轻 DB 压力。

---

### 第 12 题：Pandas 处理海量数据有哪些性能技巧？

**标准答案：**

1. **向量化**：用 NumPy/pandas 列运算，少写 `for` 循环和 `apply`
2. **分块读取**：`read_csv(chunksize=10000)` 处理放不进内存的文件
3. **类型降级**：`int64→int32`，`float64→float32`，`category` 存重复字符串
4. **只读必要列**：`usecols=[...]`
5. **先过滤再 join**，减少中间 DataFrame 体积

**项目实例：**
- 同花顺：财报批量清洗，正则提取 + pandas 标准化
- 天山数据：配置驱动规则引擎，粗清洗 + 细清洗两阶段
- 量化：K 线转 DataFrame 算 MACD/EMA，回测向量化算收益

---

### 第 13 题：Kafka 在你们数据项目里怎么用的？

**标准答案：**

在天山质量数据采集项目中，传感器和日志数据**先粗清洗**，再发到 **Kafka Topic**，下游消费者做细清洗后写入 MySQL。这样做：

1. **削峰**：采集峰值与入库速度解耦
2. **解耦**：清洗规则变更只改消费者，不影响采集端
3. **可扩展**：增加 Consumer 实例提高吞吐

Producer 配置 `acks=all` 保证不丢；Consumer 手动 commit offset；按设备 ID 分区保证同设备消息有序。

量化项目当前未用 Kafka，但架构思想类似：Webhook 快速返回 ≈ Producer，后台评分线程 ≈ 异步 Consumer。

---

### 第 14 题：JWT 认证流程？前端怎么配合？

**标准答案：**

1. 用户 POST `/api/auth/login`，服务端校验用户名密码（bcrypt 哈希）
2. 签发 JWT：`Header.Payload.Signature`，Payload 含 `user_id`、`exp`
3. 返回 token 给前端，存 `localStorage`
4. 之后请求在 Header 带 `Authorization: Bearer <token>`
5. FastAPI `Depends(require_user)` 解码校验，过期返回 401

**安全要点：**
- 密钥放环境变量，不入库
- 设置合理过期时间
- HTTPS 传输
- 敏感操作可二次验证

前端 Axios 拦截器统一加 token；401 跳登录页。

---

### 第 15 题：钉钉手动 @评分 如何识别用户回复的是哪条信号？

**标准答案：**

这是实际踩过的坑，策略名相同（如「2h进2h出」）时不能靠策略名匹配。

**解析优先级：**
1. 被回复消息正文里的 **「交易品种」**
2. 引用预览里的 **「触发时间」** → 与缓存 `trigger_time` 精确匹配（相差 1 秒的两条信号也能区分）
3. **组合匹配**：触发时间 + 被回复消息时间 + 策略名 + 买入/卖出方向，对缓存打分选唯一一条
4. 多品种同名策略仍无法区分 → 提示用户写「@我 对 TAO 2h 买入 评分」

**关键实现**：`dingtalk_manual_score.py` + `dingtalk_signal_cache.py`；只扫描被回复子树文本，避免从整包回调误扫到其他品种；`dingtalk_score_bot.py` 评分放后台线程不阻塞回调。

---

### 第 16 题：前端 React 和简历里 Vue3 有什么区别？你怎么切换的？

**标准答案：**

**相通点**：组件化、单页应用、Router 路由、Axios 调 API、状态驱动视图。

**差异：**

| | Vue3 | React（本项目） |
|---|------|-----------------|
| 响应式 | `ref`/`reactive` Proxy | `useState` 显式 setState |
| 模板 | `.vue` 单文件 | JSX |
| 构建 | Vite | Vite |

**切换成本不高**：工程化思维一致——`views` 页面、`api` 请求层、通用组件封装。本项目用 ECharts 画 K 线，用轮询刷新监控池，和 Vue 里 `onMounted` + `setInterval` 思路一样。

---

### 第 17 题：Docker 你在项目里怎么用的？

**标准答案：**

**天山项目**：Linux 上用 Docker 跑数据清洗服务，镜像里固定 Python 版本和依赖，挂载配置文件和数据目录，`docker-compose` 编排采集器 + 清洗器 + MySQL。

**量化项目**：目前以 **Shell 脚本** `start_trading_stack.sh` 三进程部署为主（API + Webhook + TV Bot），配合 `HTTP_PROXY` 访问海外 API。若上生产容器化，会把三个服务各打一个镜像，MySQL 独立容器，`.env` 注入密钥。

**Docker 价值**：环境一致、快速回滚、资源隔离。

---

### 第 18 题：如果考试系统同时要 5000 人答题，你怎么保证稳定？

**标准答案：**

**读优化：**
- 试题、试卷结构 Redis 缓存，考前预热
- 静态资源 CDN + 压缩 + 懒加载

**写优化：**
- 答卷异步提交队列（Kafka/Redis List），批量落库
- 分库分表，避免单表锁竞争

**接口层：**
- 限流（令牌桶/漏桶）
- 核心接口压测，找 P99 瓶颈
- 数据库连接池调优

**前端：**
- 倒计时、防切屏逻辑放服务端校验
- 提交按钮防抖，避免重复提交

**运维：**
- 监控 QPS、错误率、慢 SQL 告警
- 扩容时水平加 API 实例，Redis 主从

（结合自己压测数据补充具体数字更有说服力。）

---

### 第 19 题：说一个你解决过的线上 Bug 或难点

**标准答案（示例，可替换为真实经历）：**

**场景**：钉钉里回复 SOL 信号 @评分，系统却评了 BTC，因为两条信号策略名相同。

**排查**：
1. 打日志看钉钉回调 `repliedMsg` 实际内容，发现 API 常不带「交易品种」，只有策略名
2. 发现 `_collect_quote_hints` 从整包 raw 扫到另一条 ETH/BTC 正文
3. 触发时间相差 1 秒时，旧逻辑误判为歧义

**解决**：
- 只从被回复子树采集文本
- 用「触发时间 + 方向 + 策略名」组合匹配缓存
- 1 秒内多条信号取时间最近的一条，而非直接报错
- 摘要分数与展示分不一致问题，加 `harmonize_summary_score` 校准

**收获**：对接第三方 IM 不能假设 UI 上看到的内容 API 都会传回，要有**多级兜底 + 明确提示用户手动指定品种**。

---

### 第 20 题：你为什么来杭州？期望薪资 16～18K 的依据？还有什么要问我们的？

**标准答案：**

**来杭州：** 杭州互联网和金融科技岗位多，和我 Python 全栈 + 数据处理的背景匹配，希望长期在杭州发展。

**薪资依据：** 3 年 Python 经验，能独立负责全栈项目，具备数据处理、MySQL 调优、Docker 部署和 AI 接口落地能力；了解杭州同类岗位行情，16～18K 与能力和贡献相匹配，具体可根据贵司职级和团队情况协商。

**反问面试官（选 2～3 个）：**
1. 团队技术栈和核心业务方向是什么？
2. 我入职后主要负责哪块？有没有量化/数据相关场景？
3. 团队的代码评审、发布流程是怎样的？
4. 对这个岗位 3～6 个月的主要期望是什么？

---

### 模拟面试使用建议

1. **每题限时 2～3 分钟口述**，录音回听是否啰嗦
2. **第 2、4、6、8、15 题**是沐龙量化必背
3. **第 9～13 题**覆盖简历其他项目，防止面试官深挖
4. **第 19 题**准备 2 个真实 Bug 故事（数据项目 + 量化项目各一个）
5. 答案中的数字（QPS、耗时、数据量）按自己**真实压测/业务**替换，不要编造

---

*文档版本：2026-07-06 · 简历技能栈（张运繁）× 沐龙量化交易平台 · 含模拟面试 20 题*

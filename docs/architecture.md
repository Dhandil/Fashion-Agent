# Fashion-Agent 系统架构

## 1. 文档目的

本文档描述 Fashion-Agent 的系统边界、模块职责、依赖方向、核心领域、数据存储和 Agent 工作流。

产品定位与业务范围以 [产品定位与范围](./product_scope.md) 为准，可验收需求以 [需求规格](./requirements.md) 为准。

Fashion-Agent 的核心是个人穿搭决策，数字衣橱和商品搜索分别为个人化基础与按需补全能力。

---

## 2. 架构目标

系统架构需要满足：

1. API、Agent、领域、工具、RAG、Memory 和数据库相互分离。
2. 领域层不依赖 FastAPI、LangGraph、Chroma 或 SQLAlchemy。
3. 外部商品、天气和 MCP 服务可以替换，不进入核心业务逻辑。
4. PostgreSQL、Redis 和 Chroma 具有明确且不重叠的数据职责。
5. 单 Agent 稳定后可以演进为 Multi-Agent。
6. 支持异步 I/O、自动化测试和 Docker 部署。
7. 商品搜索是 Fashion Agent 的按需工具，而不是固定执行步骤。

---

## 3. 系统上下文

```text
用户或前端
    ↓ HTTP / SSE
FastAPI
    ↓
Application Service
    ↓
LangGraph Fashion Agent
    ├── LLM Provider
    ├── User Profile / Wardrobe Repository
    ├── RAG Retriever
    ├── Memory Checkpointer
    └── Tool Registry
            ├── 商品工具
            ├── 天气工具
            └── MCP 工具
```

Fashion-Agent 可以读取和组合多个来源的信息，但必须保持来源边界：

- 用户档案和衣橱来自 PostgreSQL。
- 当前对话状态来自 Memory，生产环境目标为 Redis。
- 服装通用知识来自 Chroma。
- 具体商品、价格和库存来自商品工具或授权外部服务。
- 天气等动态信息来自对应 API 或 MCP 工具。

---

## 4. 分层架构

### 4.1 API 层

职责：

- 接收和校验 HTTP 请求。
- 执行身份认证和授权。
- 将请求转换为应用用例输入。
- 返回结构化响应或流式事件。
- 将项目异常转换为统一 HTTP 错误。

API 层不直接：

- 编写 SQL。
- 访问 Chroma。
- 调用具体商品平台。
- 实现穿搭业务规则。

### 4.2 Services 应用层

职责：

- 编排一次完整应用用例。
- 获取请求级依赖。
- 装配 Agent Graph、Repository、Retriever 和 Tool。
- 管理事务边界。
- 协调领域层与外部适配器。

Services 是 API 与核心能力之间的入口，不承载具体框架模型或持久化细节。

### 4.3 Agents 层

职责：

- 定义 LangGraph 状态。
- 将任务拆分为节点。
- 根据状态选择路由。
- 决定何时检索知识或调用工具。
- 组合上下文并请求 LLM 生成最终输出。

Agents 不应直接创建数据库 Engine、读取 `.env` 或硬编码具体外部平台。

### 4.4 Domain 领域层

职责：

- 定义核心业务实体。
- 定义值对象和业务约束。
- 定义 Repository Protocol。
- 表达与具体框架无关的业务规则。

领域层是系统中最稳定的部分，不依赖 FastAPI、LangGraph、SQLAlchemy、Redis 或 Chroma。

### 4.5 Tools 工具层

职责：

- 将结构化业务能力暴露给 Agent。
- 使用 Pydantic 校验工具参数。
- 通过 Repository 或外部 Client 完成操作。
- 将结果转换为模型可以读取的结构化数据。
- 通过 Tool Registry 完成注册和发现。

工具不负责决定自己何时执行，是否调用由 Agent 路由和模型工具调用共同决定。

### 4.6 RAG 层

职责：

- 加载和切分知识文档。
- 生成 Embedding。
- 将向量写入 Chroma。
- 根据用户问题检索相关知识。
- 返回内容和来源元数据。

RAG 只负责面料、颜色、版型、季节和护理等通用知识，不提供具体商品事实。

### 4.7 Memory 层

职责：

- 保存会话级对话状态。
- 根据 `thread_id` 隔离会话。
- 提供短期 Checkpointer。
- 后续维护可控的长期用户记忆。

用户穿搭档案属于明确的结构化业务数据，应进入 PostgreSQL，而不是只存在于模型对话记忆中。

### 4.8 DB 数据库适配层

职责：

- 管理异步 SQLAlchemy Engine 和 Session。
- 定义 ORM Model。
- 在 ORM Model 与领域实体之间转换。
- 实现领域层定义的 Repository Protocol。
- 通过 Alembic 管理表结构版本。

数据库层可以依赖领域接口，领域层不能反向依赖数据库实现。

### 4.9 MCP 与外部适配层

职责：

- 连接授权的外部商品、库存、天气或企业服务。
- 将不同平台字段转换为项目统一结构。
- 管理超时、重试、认证和错误转换。
- 将 MCP Tool 接入 Tool Registry。
- 未来将 Fashion-Agent 的部分能力作为 MCP Server 对外提供。

---

## 5. 推荐依赖方向

```text
api
  ↓
services
  ├── agents
  ├── domain
  └── application ports

agents
  ├── domain
  ├── tools abstractions
  ├── rag abstractions
  └── memory abstractions

tools
  ↓
domain repository protocols

db / external clients / mcp
  ↓
domain entities and protocols
```

主要约束：

- `domain` 不导入 `api`、`agents`、`db` 或外部 SDK。
- `api` 不直接导入 ORM Model。
- `agents` 不直接执行 SQL。
- `tools` 不直接读取 FastAPI Request。
- `db` 不返回 ORM Model 给 Agent，而是转换为领域实体。
- 具体实现由 Services 或 Provider 进行依赖装配。

---

## 6. 核心领域

### 6.1 穿搭核心域

```text
StyleProfile
├── 用户长期风格偏好
├── 尺码和版型偏好
├── 颜色与材质偏好
└── 常见场景和预算

WardrobeItem
├── 用户已有衣物
├── 品类、颜色、材质和尺码
├── 季节与场景标签
└── 可用状态

Outfit
├── 一套完整穿搭
├── 场景、风格和推荐理由
└── 收藏与反馈

OutfitItem
├── Outfit 与单品的关联
├── 衣橱单品
└── 外部待购买商品
```

系统的核心产物是 `Outfit`，而不是 `Product`。

### 6.2 辅助购物域

`Product` 表示来自样例数据、缓存或外部平台的候选商品。

它可以包含：

- 项目商品 ID
- 来源平台
- 外部商品 ID
- 品类与品牌
- 价格与币种
- 颜色与尺码
- 库存状态
- 商品链接
- 同步和价格确认时间

商品域用于补全穿搭方案，不负责支付、订单、物流或售后。

---

## 7. 数据存储边界

| 存储 | 保存内容 | 不应保存 |
|---|---|---|
| PostgreSQL | 用户档案、衣橱、搭配、反馈、商品缓存 | Embedding、短期消息检查点 |
| Redis | 短期会话、临时状态、缓存、限流 | 需要永久保留的用户业务数据 |
| Chroma | 服装知识文本、向量、来源元数据 | 实时价格、库存、支付信息 |
| 外部 API/MCP | 实时商品、库存、价格、天气 | Fashion-Agent 内部会话状态 |

### 7.1 PostgreSQL 会话生命周期

PostgreSQL 使用 SQLAlchemy 2.x 和 `asyncpg`：

```text
FastAPI 请求
→ 创建 AsyncSession
→ 创建请求级 Repository
→ 创建或绑定请求级 Tool
→ graph.ainvoke()
→ 提交或回滚事务
→ 关闭 AsyncSession
```

禁止把包含请求级 `AsyncSession` 的 Repository 或 Tool 永久缓存在全局单例中。

可以缓存：

- SQLAlchemy Engine
- `async_sessionmaker`
- 不包含请求状态的 Graph 结构
- 无状态的配置对象

不应全局缓存：

- `AsyncSession`
- 数据库事务
- 绑定请求 Session 的 Repository
- 绑定请求 Session 的工具实例

### 7.2 商品数据流

开发阶段：

```text
data/samples/products.json
→ Product Loader
→ InMemoryProductRepository
→ search_products
```

数据库阶段：

```text
PostgreSQL
→ PostgresProductRepository
→ search_products
```

正式外部商品阶段：

```text
品牌 / 电商 API / MCP
→ Product Provider
→ 字段标准化与校验
→ PostgreSQL 缓存或实时结果
→ search_products
```

价格和库存属于动态信息。即使 PostgreSQL 中存在缓存，正式推荐前也应支持从来源平台重新确认。

---

## 8. Agent 工作流

### 8.1 目标工作流

```text
START
→ analyze_request
→ 判断信息是否充分
    ├── 否 → ask_clarifying_question → END
    └── 是
        ↓
→ load_style_profile
→ search_wardrobe
→ retrieve_knowledge
→ generate_outfit
→ detect_wardrobe_gap
    ├── 无缺口 → finalize_response
    ├── 有缺口但未同意购买 → ask_shopping_permission
    └── 用户明确购物 → search_products
                              ↓
                         finalize_response
→ END
```

### 8.2 商品工具调用条件

只有满足以下条件之一，Agent 才应调用商品工具：

1. 用户明确要求搜索或比较商品。
2. Agent 已说明衣橱缺口，用户同意购买。
3. 用户的问题必须依赖真实商品数据才能回答。

普通穿搭建议、面料知识和已有衣橱组合不应默认触发商品搜索。

### 8.3 当前过渡工作流

当前代码仍使用早期名称 `ShoppingAgentState` 和 `shopping` Graph，并已实现：

```text
START
→ retrieve_knowledge
→ chat
→ 判断工具调用
    ├── END
    └── tools → chat
```

该工作流可以继续作为 P0 基础，不进行一次性大规模重命名。

后续增加需求分析、用户档案、衣橱和穿搭生成节点时，再逐步演进为 Fashion Graph。

---

## 9. Tool Registry

所有 Agent Tool 应通过 Tool Registry 统一管理。

Tool Registry 负责：

- 注册工具
- 防止同名工具覆盖
- 根据名称获取工具
- 提供工作流可用工具集合
- 后续扩展权限、来源和生命周期信息

预计工具包括：

```text
search_wardrobe
save_wardrobe_item
get_style_profile
save_style_preference
retrieve_fashion_knowledge
get_weather
search_products
get_product_detail
compare_products
```

工具参数必须使用 Pydantic Schema，工具结果应优先返回结构化 JSON。

---

## 10. RAG 架构

```text
知识文件
→ Loader
→ Text Splitter
→ Embedding
→ Chroma
→ Retriever
→ Agent Context
```

知识片段应保存：

- 稳定片段 ID
- 来源路径或 URL
- 文档类型
- 版本或更新时间
- 片段正文

RAG 结果只能作为参考知识。具体用户数据以 PostgreSQL 为准，具体商品数据以 Tool 或外部平台为准。

---

## 11. Memory 架构

### 11.1 短期 Memory

当前开发环境使用 LangGraph `InMemorySaver`。

生产目标是 Redis Checkpointer，并支持：

- `conversation_id` 与 `thread_id` 映射
- 会话 TTL
- 多实例共享
- 服务重启后恢复
- 会话隔离

### 11.2 长期资料

用户明确保存的偏好、衣橱和搭配属于业务数据，进入 PostgreSQL。

LLM 从对话中推断出的临时信息不应未经用户确认自动成为永久资料。

---

## 12. MCP 与 Multi-Agent

### 12.1 MCP

MCP Client 主要用于接入：

- 外部商品平台
- 企业库存服务
- 天气服务
- 其他授权工具

MCP Server 可以对外提供：

- 穿搭建议
- 衣橱检索
- 服装知识检索
- 经授权的商品发现能力

### 12.2 Multi-Agent

单 Agent 稳定后，可以演进为：

```text
Fashion Supervisor
├── Profile Agent
├── Wardrobe Agent
├── Styling Agent
├── Knowledge Agent
└── Shopping Agent
```

Multi-Agent 只改变内部任务协作方式，不应破坏 API、领域实体和数据访问边界。

---

## 13. 目录结构与职责

```text
Fashion-Agent/
├── app/
│   ├── api/
│   │   ├── dependencies/      # FastAPI 请求级依赖
│   │   ├── routers/           # HTTP 路由
│   │   └── schemas/           # API 请求和响应模型
│   ├── agents/
│   │   ├── graphs/            # LangGraph 工作流
│   │   ├── nodes/             # 可复用 Agent 节点
│   │   ├── prompts/           # 系统提示词和提示模板
│   │   ├── routing/           # 条件路由
│   │   ├── state/             # Agent 状态模型
│   │   └── multi_agent/       # Multi-Agent 扩展
│   ├── core/                  # 配置、异常、日志和安全
│   ├── db/
│   │   ├── mappers/           # ORM Model 与领域实体转换
│   │   ├── models/            # SQLAlchemy ORM Model
│   │   ├── repositories/      # Repository 具体实现
│   │   └── session.py         # Engine 和 Session 工厂
│   ├── domain/
│   │   ├── entities/          # 领域实体
│   │   ├── repositories/      # Repository Protocol
│   │   └── value_objects/     # 不可变值对象
│   ├── llm/
│   │   └── providers/         # LLM 适配器
│   ├── memory/
│   │   ├── short_term/        # 对话 Checkpointer
│   │   └── long_term/         # 长期记忆编排
│   ├── mcp/
│   │   ├── client/            # MCP Client
│   │   └── server/            # MCP Server
│   ├── observability/         # 日志、指标和链路追踪
│   ├── rag/
│   │   ├── embeddings/        # Embedding 适配
│   │   ├── loaders/           # 文档加载和切分
│   │   ├── retrievers/        # 检索器
│   │   └── vectorstores/      # Chroma 适配
│   ├── services/              # 应用用例和依赖装配
│   └── tools/
│       ├── builtins/          # 衣橱、天气和商品等工具
│       └── registry/          # Tool Registry
├── data/
│   ├── raw/                   # 未处理知识数据
│   ├── processed/             # 清洗和切分产物
│   └── samples/               # 可提交的开发样例
├── deployments/
│   ├── docker/                # Docker 和 Compose 配置
│   └── kubernetes/            # Kubernetes 扩展
├── docs/                      # 产品、需求和架构文档
├── migrations/
│   └── versions/              # Alembic 迁移版本
├── scripts/                   # 导入、索引和维护脚本
├── tests/
│   ├── unit/                  # 快速单元测试
│   ├── integration/           # 基础设施集成测试
│   └── e2e/                   # API 到 Agent 的端到端测试
├── alembic.ini                # Alembic 配置
├── .env.example               # 可提交的环境变量模板
└── pyproject.toml             # 项目和开发工具配置
```

目录结构表示稳定的职责边界。只有出现真实业务代码时才创建新的细分模块，避免为了目录完整而创建无意义的空层。

---

## 14. 部署拓扑

开发阶段目标：

```text
Docker Compose
├── api
├── postgres
└── redis

Chroma
└── 初期使用本地持久化目录
```

后续可以将 Chroma 切换为独立服务，并增加反向代理、监控和任务 Worker。

生产环境中的 Secret 不写入镜像、Compose 文件或 Git，由部署环境注入。

---

## 15. 测试策略

### 单元测试

- 领域实体和规则
- Mapper
- Repository 查询构造
- Tool 参数与输出
- Agent Node 和 Routing
- 配置和异常

### 集成测试

- FastAPI 路由
- PostgreSQL Repository
- Redis Checkpointer
- Chroma 检索
- MCP Client 与 Server

### 端到端测试

- 用户请求到穿搭回答
- 多轮会话
- RAG 引用
- 按需商品工具调用
- 外部服务失败时的降级

测试默认不调用真实付费模型和生产外部服务，除非明确标记为手动或端到端测试。

---

## 16. 演进原则

1. 先保持单 Agent 工作流稳定，再拆分 Multi-Agent。
2. 先使用样例商品验证工具边界，再接入真实平台。
3. 先建立领域接口，再实现 PostgreSQL、Redis 或 MCP 适配器。
4. 采用渐进式重构，不一次性重命名所有 `shopping` 模块。
5. 每次新增节点、工具或存储实现，都补充对应测试。
6. 文档、领域模型和实际行为保持同步。

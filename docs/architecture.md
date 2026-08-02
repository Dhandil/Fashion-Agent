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

- 读取正式发布 Manifest，而不是递归扫描独立知识库。
- 按原始文件字节校验 SHA-256。
- 解析 Markdown Frontmatter 和 S01、S02 等稳定章节。
- 只接收已批准并允许发布到 RAG 的知识。
- 在稳定章节内执行二次切分。
- 生成 Embedding。
- 将向量写入 Chroma。
- 根据用户问题检索相关知识。
- 返回内容和来源元数据。

RAG 只负责面料、颜色、版型、季节和护理等通用知识，不提供具体商品事实。
独立知识库中的 `sources/`、`staging/`、`archive/` 和 `evaluation/`
不进入 Chroma。用户衣橱、商品、实时天气和 Memory 继续由各自的数据源
负责，不通过知识入库流程写入。

### 4.7 Memory 层

职责：

- 保存会话级对话状态。
- 根据 `thread_id` 隔离会话。
- 提供短期 Checkpointer。
- 在模型输入侧保留最近有限个完整对话轮次，不切断当前轮工具调用链。
- 把退出最近窗口的人机文本压缩为本地提取式滚动摘要，排除 ToolMessage。
- 后续维护可控的长期用户记忆。

用户穿搭档案属于明确的结构化业务数据，应进入 PostgreSQL，而不是只存在于模型对话记忆中。

滚动摘要只帮助理解连续意图，不是衣橱、商品、价格、库存、天气或购物授权的
权威来源。动态事实必须重新读取当前 Repository、Provider 或 Tool。摘要随短期
Checkpointer 保存，不自动写入 Style Profile 或其他长期记忆；日志只记录摘要
覆盖消息数和字符数，不记录摘要正文。

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
├── 用户明确避免的风格
├── 尺码和版型偏好
├── 喜欢与避免的颜色、材质偏好
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

OutfitRecommendation
├── Agent 本轮生成但尚未保存的结构化穿搭
├── 不包含用户 ID、数据库 ID 或收藏状态
├── 记录每个单品的来源和来源引用 ID
└── 记录与具体搭配单品对应的衣橱缺口
```

系统的核心产物是 `Outfit`，而不是 `Product`。

`StyleProfile` 只保存用户主动提供或明确确认的长期偏好。喜欢和避免的
风格、颜色必须互斥；序列字段在进入领域实体时统一去除首尾空格、空项和
大小写重复项。

Style Profile 当前提供：

- `GET /api/v1/style-profile`：查询当前用户档案。
- `PUT /api/v1/style-profile`：完整替换档案，未提供的字段会恢复默认值。
- `PATCH /api/v1/style-profile`：只更新明确提供的字段，偏好列表使用空数组
  表示清空，不能使用 `null`。
- `GET /api/v1/style-profile/candidates`：根据 Outfit 反馈生成可追溯的风格
  偏好候选，不写入档案。
- `POST /api/v1/style-profile/candidates/confirm`：重新校验当前证据后，把
  用户确认的候选写入档案。

PATCH 请求先与当前档案合并，再通过领域实体重新校验。若局部修改与已有
喜欢/避免项或预算范围冲突，API 返回结构化 409，且不会写入数据库。
候选确认接口不信任客户端提交的证据数量，而是重新读取当前反馈和 Outfit
计算候选，避免过期或伪造的候选修改长期资料。

Wardrobe 当前提供：

- `POST /api/v1/wardrobe`：为当前用户新增衣橱单品。
- `GET /api/v1/wardrobe`：按品类、可用状态和 `limit/offset` 查询衣橱，
  同时返回相同过滤条件下的总数。
- `GET /api/v1/wardrobe/{wardrobe_item_id}`：查询单品详情。
- `PATCH /api/v1/wardrobe/{wardrobe_item_id}`：只修改请求中明确提供的字段。
- `PATCH /api/v1/wardrobe/{wardrobe_item_id}/status`：为界面上的可用状态
  开关提供明确入口。
- `DELETE /api/v1/wardrobe/{wardrobe_item_id}`：删除当前用户的单品。

所有衣橱接口都由身份依赖提供 `user_id`，请求体和 LLM 不能指定用户。
详情、修改和删除统一使用 `user_id + wardrobe_item_id` 定位记录；不存在
和属于其他用户的 ID 返回相同的 `wardrobe_item_not_found`，避免泄露
其他用户的衣橱。PATCH 先合并当前领域实体，再执行完整校验；空 PATCH
不会产生数据库写入。

`OutfitRecommendation` 是 Agent 与 API 之间的候选方案。
只有用户明确保存时，应用服务才为它补充服务端生成的 `outfit_id` 和当前
`user_id`，并转换为需要持久化的 `Outfit`。

当前确认保存流程为：

```text
POST /api/v1/outfits
→ 客户端只提交 conversation_id
→ 服务端使用当前 user_id 读取对应 LangGraph State
→ 取得最后一套已校验 OutfitRecommendation
→ 根据 user_id + conversation_id 生成稳定 outfit_id
→ OutfitRepository 保存到 PostgreSQL
```

客户端不能重新提交整套推荐内容，因此不能在确认阶段篡改 `user_id` 或
来源引用 ID。同一用户重复确认同一会话时复用相同 `outfit_id`，避免网络
重试产生重复记录。当前持久化模型保存正式采用的 `items`，不把备选项和
衣橱缺口自动转换成已拥有衣物。

已保存 Outfit 的读取接口包括：

- `GET /api/v1/outfits`：查询当前用户的穿搭列表，支持场景、收藏状态和
  Offset 分页。
- `GET /api/v1/outfits/{outfit_id}`：查询当前用户的一套穿搭详情。
- `PATCH /api/v1/outfits/{outfit_id}/favorite`：由用户明确收藏或取消收藏。

这些接口都由服务端注入 `user_id`。不存在的 ID 和属于其他用户的 ID
统一返回 `outfit_not_found`，避免通过响应差异枚举其他用户数据。

收藏操作先读取当前用户的完整 `Outfit`，再通过不可变对象复制更新
`is_favorite`，最后由仓库保存。收藏状态不由 LLM 自动修改。

列表分页响应包含：

- `items`：当前页 Outfit。
- `count`：当前页实际返回数量。
- `total`：相同筛选条件下的总记录数。
- `limit`：当前页最大数量。
- `offset`：本次查询跳过的记录数。

分页和总数统计都在仓库层执行。PostgreSQL 使用 `LIMIT/OFFSET` 和独立
`COUNT(*)`，不会为了分页把当前用户的全部 Outfit 加载进应用内存。

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

当前实现把模型、RAG Retriever 和 Checkpointer 组成无请求状态的共享运行资源。
每次聊天请求单独创建 Tool Registry，将当前用户身份和衣橱 Repository
绑定到 `search_wardrobe`，再编译本次请求使用的 Graph。
不同请求可以共享对话 Checkpointer，但不能共享绑定数据库 Session 的衣橱工具。

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
→ prepare_turn
→ load_style_profile
→ load_recent_outfits
→ load_outfit_feedback
→ retrieve_knowledge
→ chat
→ 判断工具调用
    ├── 普通回答 → END
    └── tools
          ├── search_wardrobe（请求级、当前用户）
          └── search_products（共享、按需购物）
              ↓
            chat
              ├── 当前轮未查询衣橱 → END
              └── 当前轮已查询衣橱
                    ↓
              generate_outfit
                    ↓
                  END
```

`generate_outfit` 使用结构化 LLM 输出生成 `OutfitRecommendation`。
当前 DeepSeek 模型默认可能启用 Thinking Mode，因此该节点使用 JSON Output，
不使用会强制指定 `tool_choice` 的 Function Calling。JSON 结果仍需经过
Pydantic 结构校验和来源 ID 校验后才能进入 API 响应。

衣橱和商品来源 ID 必须出现在当前轮对应工具的结果中；通用建议不能携带
伪造 ID。`prepare_turn` 会先把上一轮成功生成的
`outfit_recommendation` 保存为 `previous_outfit_recommendation`，
再清空本轮输出，避免 Checkpointer 中的旧推荐泄漏到当前响应。

`load_recent_outfits` 读取当前用户最近保存的有限 Outfit，并整理场景、
风格和衣橱单品组合。近期记录只是减少完全重复的软约束：衣橱选择有限、
场景需要或用户明确要求时可以复用。它们属于数据，不作为系统指令执行。

当用户提出“换一件上衣”或“更休闲一点”等调整要求时，聊天和结构化生成
节点可以读取 `previous_outfit_recommendation`，保留未要求改变且仍符合
当前条件的部分。历史推荐不提供新的来源授权；调整后的所有衣橱和商品 ID
仍必须出现在当前轮工具结果中。

天气通过两条路径进入同一个 `WeatherContext` 语义：

```text
客户端明确提供天气
→ ChatRequest.weather
→ WeatherContext(source=user_provided)
→ ShoppingAgentState.weather_context

第三方天气 API / MCP
→ WeatherProvider
→ get_weather Tool
→ 当前轮 ToolMessage
```

`WeatherProvider` 是领域层协议，只规定按照地点和日期返回天气，不依赖
具体 SDK。API 或 MCP 适配器可以替换，而 Agent 只接触 `get_weather` 工具
和标准化结果。当前已有 Open-Meteo 适配器：先通过 Geocoding API 把地点
转换为经纬度和时区，再通过 Forecast API 读取目标日期的天气代码、温度、
体感、降雨概率和最大风速。接口字段依据
[Open-Meteo Forecast API](https://open-meteo.com/en/docs) 和
[Geocoding API](https://open-meteo.com/en/docs/geocoding-api)。

具体适配器由 `integrations/weather` 实现，并由配置工厂装配：

```text
WEATHER_PROVIDER_BACKEND=disabled
→ 返回 None
→ 请求级 Tool Registry 不注册 get_weather

WEATHER_PROVIDER_BACKEND=open_meteo
→ OpenMeteoWeatherProvider
→ 请求级 Tool Registry 注册 get_weather
→ Agent 按需查询
```

公共端点只作为非商业开发原型使用，默认保持关闭。商业生产环境必须显式
配置 API Key，并切换到具有商业授权的客户端点或经许可的自托管端点。
生产环境缺少 Key 时，Provider 工厂直接抛出配置错误，避免误用公共服务。
Open-Meteo 数据还涉及署名要求，产品界面和正式部署需要按其最新授权条款
提供归属说明。

HTTP 超时、上游错误、地点不存在和响应字段缺失统一转换为项目天气异常。
`get_weather` 捕获该异常并返回结构化不可用结果；该对象不是天气记录，
因此不会进入结构化 Outfit 的天气事实列表，也不会中断整次 Agent 对话。
此时 Agent 只能请求用户提供天气或给出明确标注条件的季节性建议。

天气包含地点、目标日期、天气状况、最低/最高温、体感温度、降雨概率、
湿度、风速、来源和更新时间。至少需要存在一项天气事实，最低温不能高于
最高温。每个聊天请求都会明确写入天气或 `None`，防止 Checkpointer 把
上一轮天气误用于新请求。天气只影响当前 Outfit，不保存到 Style Profile
或 PostgreSQL。

领域层的天气规则会把已知事实转换为额外的 `outfit_guidance`：

- 高温或高体感温度：轻薄、透气、吸湿并减少厚重层次。
- 低温：增加保暖内层和外层。
- 昼夜温差较大：采用方便穿脱的分层。
- 明显降水：考虑防水外层、耐水防滑鞋履或雨具。
- 大风：考虑防风和单品固定性。
- 高温高湿：考虑快干、透气和不易贴肤的材质。

规则只读取实际存在的字段，缺失字段不会触发推测。客户端天气由 Chat Node
计算约束；天气工具则把相同约束随结构化结果返回。结构化 Outfit 节点按照
“天气工具结果优先于客户端天气”的顺序选择事实并重新计算约束。这样关键
天气风险不是完全交给 LLM 临时判断，同时仍保留模型结合场景和衣橱选择
具体单品的空间。

只有当前轮实际调用 `search_wardrobe` 才进入该节点，因此普通知识问答和
单独的商品搜索不会额外执行结构化 Outfit 模型调用。

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

当前默认注册 `search_products`，每个请求额外注册绑定当前用户的
`search_wardrobe`。`get_weather` 已实现，但只有装配具体
`WeatherProvider` 时才进入请求级注册表，避免在没有真实数据源时向模型
暴露一个无法执行的工具。

---

## 10. RAG 架构

```text
发布 Manifest
→ 文档路径白名单与 SHA-256 校验
→ Frontmatter 发布门禁
→ S01、S02 等稳定章节解析
→ 章节内 Text Splitter
→ Embedding
→ Chroma
→ 扩大候选集的向量召回
→ 标题、标签和正文词面信息本地重排
→ Agent Context
```

知识片段应保存：

- `fragment_id`
- `knowledge_id`
- `doc_type`
- `version`
- `updated_at`
- `source_ids`
- `source_path_or_url`
- 片段正文

`fragment_id` 使用
`{knowledge_id}::{section_id}::{split_sequence}`，其中序号在每个稳定
章节内从 `001` 重新开始。来源路径始终使用 Manifest 中的 POSIX 相对
路径，不能写入开发者本机绝对路径。

稳定章节经过二次切分后，每个片段正文都会补充文档标题、知识类型、标签
和稳定章节编号。这样即使片段主体只剩表格或代码块，Embedding 仍保留其
所属知识主题；这些检索上下文不改变稳定 `fragment_id`。

Retriever 先读取 `RAG_CANDIDATE_K` 个向量候选，再按知识标签、标题、正文
词面匹配和原始向量顺序执行确定性重排，最终只返回 `RAG_TOP_K` 个片段。
没有词面线索时仍保持原始向量相关性顺序。

所有 Manifest 文档必须在任何 Chroma 写入前完成完整性和结构校验；任一
文档失败时，本批次不能产生部分写入。检索结果按命中片段返回
`fragment_id` 与 `source_path_or_url`，用于回答来源审计。

`fashion_knowledge` collection 是正式知识专用集合。同步新发布时先
upsert 本次全部片段；只有新片段写入成功后，才清理集合中不属于当前
Manifest 的旧 ID，防止历史示例或已撤回片段继续被召回。

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
│   │   ├── context.py         # 当前轮消息边界等对话上下文辅助函数
│   │   ├── graphs/            # LangGraph 工作流
│   │   ├── nodes/             # 可复用 Agent 节点
│   │   ├── prompts/           # 系统提示词和提示模板
│   │   ├── routing/           # 条件路由
│   │   ├── schemas/           # Agent 内部结构化输出模型
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
│   │   ├── policies/          # 天气等可测试的领域决策规则
│   │   ├── repositories/      # Repository Protocol
│   │   └── value_objects/     # 不可变值对象
│   ├── llm/
│   │   └── providers/         # LLM 适配器
│   ├── integrations/
│   │   └── weather/           # Open-Meteo 等第三方天气 API 适配器
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

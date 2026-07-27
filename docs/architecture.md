# Fashion-Agent 架构与目录职责

## 分层关系

请求从 `api` 进入，由 `services` 编排应用用例，再调用 `agents`。Agent 图可以使用
`tools`、`rag` 和 `memory`，这些模块通过适配层访问 LLM、PostgreSQL、Redis、Chroma
或外部 MCP 服务。`domain` 保持独立，不依赖 Web 框架和具体存储实现。

## 目录结构

```text
Fashion-Agent/
├── app/
│   ├── api/
│   │   ├── dependencies/      # FastAPI 依赖注入
│   │   ├── routers/           # HTTP 路由，按资源或版本拆分
│   │   └── schemas/           # API 请求/响应 Pydantic 模型
│   ├── agents/
│   │   ├── graphs/            # LangGraph 图定义与装配
│   │   ├── nodes/             # 可复用 Agent 节点
│   │   ├── routing/           # 意图识别和路由策略
│   │   ├── state/             # 图状态和上下文模型
│   │   └── multi_agent/       # 多 Agent 协作与监督器扩展
│   ├── core/                  # 配置、异常、日志、安全等横切能力
│   ├── db/
│   │   ├── models/            # ORM 持久化模型
│   │   └── repositories/      # 仓储实现与数据访问
│   ├── domain/
│   │   ├── entities/          # 领域实体与业务规则
│   │   └── value_objects/     # 不可变值对象
│   ├── llm/
│   │   └── providers/         # DeepSeek/OpenAI 兼容适配器
│   ├── memory/
│   │   ├── short_term/        # 会话状态、检查点和短期记忆
│   │   └── long_term/         # 用户画像、偏好和长期记忆
│   ├── mcp/
│   │   ├── client/            # 外部 MCP Server 客户端
│   │   └── server/            # 对外暴露能力的 MCP Server
│   ├── observability/         # 日志、指标、链路追踪和审计
│   ├── rag/
│   │   ├── embeddings/        # Embedding 模型适配
│   │   ├── loaders/           # 文档采集、解析与切分
│   │   ├── retrievers/        # 检索、过滤和重排
│   │   └── vectorstores/      # Chroma 等向量库适配
│   ├── services/              # 应用用例编排，连接 API 与领域能力
│   └── tools/
│       ├── builtins/          # 商品、价格、库存、尺码等内置工具
│       └── registry/          # Tool 注册、发现、权限与生命周期
├── data/
│   ├── raw/                   # 未处理的本地知识数据（默认不提交）
│   └── processed/             # 清洗/切分产物（默认不提交）
├── deployments/
│   ├── docker/                # Dockerfile、Compose 配置扩展位
│   └── kubernetes/            # Kubernetes 部署清单扩展位
├── docs/                      # 架构、需求、设计决策和运维文档
├── migrations/versions/       # PostgreSQL 数据库迁移版本
├── scripts/                   # 初始化、导入、维护等一次性脚本
├── tests/
│   ├── unit/                  # 无外部依赖的快速单元测试
│   ├── integration/           # 数据库、缓存、向量库和 MCP 集成测试
│   └── e2e/                   # 从 API 到 Agent 的端到端测试
├── .env.example               # 可提交的环境变量模板
├── pyproject.toml             # 包元数据及开发工具配置
└── requirements.txt           # 暂时保留的部署依赖入口
```

## 依赖方向

推荐依赖方向为 `api -> services -> domain`。`agents` 由服务层调用，并通过抽象接口使用
`tools`、`rag`、`memory` 和 `llm`。外部系统的具体实现放在相应适配模块中，避免
FastAPI、LangGraph、Chroma 或数据库细节进入领域层。

## 预期 Agent 工作流

用户输入 → 需求分析节点 → 路由节点 → RAG / Tool / Memory → 推荐生成节点 → API 响应。
后续引入 Multi-Agent 时，可以在 `multi_agent` 中增加 Supervisor 和专业 Agent，
无需改变 API 与领域模型的边界。

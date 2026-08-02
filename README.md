# Fashion-Agent

面向年轻用户的企业级 AI 穿搭与衣橱助手。系统通过自然语言理解场景、天气、
个人偏好和衣橱可用状态，优先生成可执行的穿搭建议；商品搜索是衣橱不足或用户
明确表达购物意图时才启用的附加能力。

项目已经具备 FastAPI、LangGraph、RAG、衣橱、Outfit、用户反馈、长期偏好、
PostgreSQL 和基础可观测性等核心链路，并持续通过确定性测试和模型评测验证。

## 当前能力

- 场景、天气、风格、预算和购物权限的结构化需求分析
- 基于 Manifest、SHA-256 和稳定片段 ID 的服装知识 RAG
- 衣橱可用性筛选、结构化 Outfit 生成、校验和确定性修正
- Outfit 保存、收藏、反馈以及需用户确认的长期偏好候选
- PostgreSQL 持久化、Alembic 迁移和可追溯偏好记忆
- 商品搜索 Tool、Tool Registry 与外部天气 Provider 扩展边界

## 技术栈

- Python 3.11、FastAPI、Pydantic
- LangGraph、LangChain
- DeepSeek / OpenAI 兼容 API
- RAG、Chroma
- PostgreSQL、Docker
- Redis、MCP、Multi-Agent（后续扩展）

## 文档

- [架构与目录职责](docs/architecture.md)
- [产品定位与边界](docs/product_scope.md)
- [需求规格](docs/requirements.md)
- [开发路线图](docs/roadmap.md)

## 开发约定

- 应用代码统一位于 `app/`，测试按 `unit`、`integration`、`e2e` 分层。
- 本地配置从 `.env.example` 复制到 `.env`；严禁提交密钥。
- `data/raw/`、`data/chroma/`、`.env` 和 `.venv/` 不进入 Git。
- 依赖声明以 `pyproject.toml` 为准；新增依赖前先评估必要性和运行成本。

## 发布前检查

不依赖 Docker 的默认质量门：

```powershell
python -m scripts.check_quality
```

PostgreSQL 容器健康且数据库已经迁移到最新版本时，可以运行完整质量门：

```powershell
python -m scripts.check_quality --postgres
```

完整模式会额外执行 Alembic 模型一致性检查和真实 PostgreSQL Repository 测试。
脚本会先阻止 `.env`、原始知识文件、Chroma 运行数据或虚拟环境被 Git 跟踪。

应用与 PostgreSQL 已启动时，可以执行不调用模型、不会写入业务数据的 API 冒烟检查：

```powershell
python -m scripts.smoke_api
```

它只使用隔离的开发身份读取进程健康、数据库就绪、Style Profile、偏好记忆、
衣橱和已保存 Outfit 列表。服务运行在其他地址时可通过 `--base-url` 指定。

## Docker Compose

只验证 Compose 结构，不构建或下载镜像：

```powershell
docker compose -f deployments/docker/compose.yaml config --quiet
```

首次完整启动会下载 Python 基础镜像和项目依赖，因此应确认网络与磁盘空间后执行：

```powershell
docker compose -f deployments/docker/compose.yaml up --build -d
```

Compose 会先等待 PostgreSQL 健康，再运行一次 Alembic migration，成功后启动 API。
应用使用非 root 用户；原始知识库以只读方式挂载，Chroma 和 Hugging Face 缓存
独立持久化，不会被复制进镜像。

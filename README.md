# Fashion-Agent

面向年轻用户的企业级 AI Shopping Assistant。系统将通过自然语言理解购买需求，
结合服装知识、商品信息和用户偏好，提供商品搜索、穿搭、尺码和购买建议。

当前仓库处于项目骨架阶段：只定义模块边界、工程配置和扩展位置，不包含业务实现。

## 规划能力

- 购买需求分析：品类、场景、季节、风格与预算
- 基于 RAG 的服装知识问答
- 商品搜索、比较与库存查询工具
- 用户风格、尺码与历史选择记忆
- Tool Registry、MCP Client/Server 和 Multi-Agent 扩展

## 技术栈

- Python 3.11、FastAPI、Pydantic
- LangGraph、LangChain
- DeepSeek / OpenAI 兼容 API
- RAG、Chroma
- PostgreSQL、Redis
- MCP、Docker

## 文档

- [架构与目录职责](docs/architecture.md)
- [产品需求](docs/requirements.md)

## 开发约定

- 应用代码统一位于 `app/`，测试按 `unit`、`integration`、`e2e` 分层。
- 本地配置从 `.env.example` 复制到 `.env`；严禁提交密钥。
- 依赖声明以 `pyproject.toml` 为主，待选型稳定后再添加运行和开发依赖。

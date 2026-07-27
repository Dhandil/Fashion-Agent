# Fashion Agent

## 项目介绍

Fashion Agent 是一个面向年轻用户的 AI 购物助手。

用户可以通过自然语言描述自己的购买需求，
Agent 可以理解用户需求，结合服装知识库、
商品信息和用户偏好，为用户提供服装推荐。

---

## 项目目标

打造一个具备：

- 用户需求理解
- 商品搜索
- 穿搭建议
- 尺码推荐
- 用户偏好记忆

能力的智能购物 Agent。

---

## 核心能力

### 1. 智能需求分析

理解：

- 品类
- 场景
- 季节
- 风格
- 预算


### 2. 服装知识问答

基于 RAG：

回答：

- 面料特点
- 版型区别
- 穿搭建议


### 3. 商品工具调用

通过 Agent Tool：

实现：

- 商品查询
- 商品比较
- 库存查询


### 4. 用户记忆

记录：

- 风格偏好
- 尺码信息
- 历史选择


---

## 技术栈

Backend:
- Python
- FastAPI

Agent:
- LangGraph
- LangChain

LLM:
- DeepSeek API

Knowledge:
- RAG
- Chroma

Database:
- PostgreSQL
- Redis

Deployment:
- Docker
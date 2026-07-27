# Fashion Agent Architecture


## 总体架构


User

↓

FastAPI

↓

LangGraph Agent


↓

--------------------------------

|              |              |

Memory         RAG          Tools


|

用户画像


|

PostgreSQL



RAG:

服装知识库

Vector Database



Tools:

商品查询

价格比较

尺码推荐



--------------------------------



## Agent Workflow


用户输入

↓

需求分析Node

↓

Router Node

↓

选择:

RAG

或者

Tool

↓

推荐生成Node

↓

返回结果


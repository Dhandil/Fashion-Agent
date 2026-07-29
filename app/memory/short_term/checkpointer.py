from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver


@lru_cache
def get_short_term_checkpointer() -> InMemorySaver:
    """创建并缓存开发环境使用的内存检查点存储器。"""

    # InMemorySaver 将对话状态保存在当前 Python 进程的内存中
    return InMemorySaver()
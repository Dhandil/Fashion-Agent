"""Redis Checkpointer 真实持久化集成测试。"""

import operator
import os
from typing import Annotated, TypedDict
from uuid import uuid4

import pytest
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.memory.short_term.checkpointer import (
    close_short_term_checkpointer,
    get_short_term_checkpointer,
    initialize_short_term_checkpointer,
)

# 默认测试套件不连接本地 Redis，只有质量门显式启用时才运行
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_TESTS") != "true",
    reason="需要设置 RUN_REDIS_TESTS=true 并启动 Redis 8",
)


class RedisTestState(TypedDict):
    """用于验证跨 Checkpointer 实例累积状态的最小图状态。"""

    values: Annotated[list[str], operator.add]


def create_test_graph(
    checkpointer: AsyncRedisSaver,
):
    """创建不调用模型和业务工具的最小状态图。"""

    builder = StateGraph(RedisTestState)
    builder.add_node("complete", lambda _state: {})
    builder.add_edge(START, "complete")
    builder.add_edge("complete", END)
    return builder.compile(checkpointer=checkpointer)


@pytest.mark.anyio
async def test_redis_restores_state_across_saver_instances() -> None:
    """验证模拟进程重启后可以恢复同一会话状态。"""

    redis_url = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )
    thread_id = f"fashion-agent-redis-test-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    ttl = {"default_ttl": 5, "refresh_on_read": True}

    first_saver = AsyncRedisSaver(redis_url=redis_url, ttl=ttl)
    await first_saver.asetup()
    try:
        first_graph = create_test_graph(first_saver)
        first_result = await first_graph.ainvoke(
            {"values": ["first"]},
            config=config,
        )
        assert first_result["values"] == ["first"]
    finally:
        await first_saver.__aexit__(None, None, None)

    # 使用全新的连接和 Saver，模拟应用进程已经重启
    second_saver = AsyncRedisSaver(redis_url=redis_url, ttl=ttl)
    await second_saver.asetup()
    try:
        second_graph = create_test_graph(second_saver)
        second_result = await second_graph.ainvoke(
            {"values": ["second"]},
            config=config,
        )
        assert second_result["values"] == [
            "first",
            "second",
        ]

        # 集成测试结束后删除专用 thread，不留下测试会话数据
        await second_saver.adelete_thread(thread_id)
        assert await second_saver.aget_tuple(config) is None
    finally:
        await second_saver.__aexit__(None, None, None)


@pytest.mark.anyio
async def test_redis_prunes_old_checkpoints_and_keeps_latest_state() -> None:
    """验证裁剪历史快照后，最新完整状态仍能继续恢复和累积。"""

    redis_url = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )
    thread_id = f"fashion-agent-redis-prune-test-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    saver = AsyncRedisSaver(
        redis_url=redis_url,
        ttl={"default_ttl": 5, "refresh_on_read": True},
    )
    await saver.asetup()

    try:
        graph = create_test_graph(saver)
        for value in ("first", "second", "third"):
            await graph.ainvoke(
                {"values": [value]},
                config=config,
            )

        checkpoints_before = [checkpoint async for checkpoint in saver.alist(config)]
        assert len(checkpoints_before) > 2

        await saver.aprune(
            [thread_id],
            keep_last=2,
        )

        checkpoints_after = [checkpoint async for checkpoint in saver.alist(config)]
        assert len(checkpoints_after) == 2

        result = await graph.ainvoke(
            {"values": ["fourth"]},
            config=config,
        )
        assert result["values"] == [
            "first",
            "second",
            "third",
            "fourth",
        ]
    finally:
        await saver.adelete_thread(thread_id)
        await saver.__aexit__(None, None, None)


@pytest.mark.anyio
async def test_project_provider_initializes_and_closes_redis(
    monkeypatch,
) -> None:
    """验证项目生命周期工厂能够初始化并释放真实 Redis Saver。"""

    monkeypatch.setenv("SHORT_TERM_MEMORY_BACKEND", "redis")
    monkeypatch.setenv(
        "REDIS_URL",
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )
    monkeypatch.setenv("REDIS_CHECKPOINT_TTL_MINUTES", "5")
    get_settings.cache_clear()
    get_short_term_checkpointer.cache_clear()

    try:
        await initialize_short_term_checkpointer()
        checkpointer = get_short_term_checkpointer()
        assert isinstance(checkpointer, AsyncRedisSaver)
    finally:
        await close_short_term_checkpointer()
        get_settings.cache_clear()

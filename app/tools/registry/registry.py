from langchain_core.tools import BaseTool

from app.core.exceptions import ToolRegistryError


class ToolRegistry:
    """统一管理 Agent 可以使用的工具。"""

    def __init__(self) -> None:
        """初始化空的工具注册表。"""

        # 使用工具名称作为键，工具对象作为值
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个 LangChain 工具。"""

        # 禁止同名工具静默覆盖
        if tool.name in self._tools:
            raise ToolRegistryError(
                f"工具 {tool.name} 已经注册",
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """根据名称获取已注册的工具。"""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRegistryError(
                f"找不到工具 {name}",
            ) from exc

    def list_tools(self) -> tuple[BaseTool, ...]:
        """返回所有已注册工具的只读快照。"""

        return tuple(self._tools.values())
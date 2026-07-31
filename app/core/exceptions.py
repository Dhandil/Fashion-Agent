class FashionAgentError(Exception):
    """Fashion-Agent 项目的基础异常。

    项目中自定义的异常都继承这个类，
    方便后续同意识别和处理项目内部错误。
    """


class ConfigurationError(FashionAgentError):
    """配置错误。
    
    当必要的环境变量缺失或配置值不合法时抛出。
    """


class ToolRegistryError(FashionAgentError):
    """工具注册表错误。
    
    当工具重复注册、工具不存在或注册信息不合法时抛出。
    """


class OutfitRecommendationNotFoundError(
    FashionAgentError,
):
    """当前会话中没有可确认保存的穿搭推荐。"""

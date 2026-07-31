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


class OutfitNotFoundError(FashionAgentError):
    """当前用户不存在指定的已保存穿搭。"""


class OutfitFeedbackNotFoundError(FashionAgentError):
    """当前用户尚未对指定的已保存穿搭提供反馈。"""


class PreferenceCandidateUnavailableError(
    FashionAgentError,
):
    """用户尝试确认的偏好候选已不存在或证据不足。"""


class StyleProfileUpdateConflictError(
    FashionAgentError,
):
    """部分更新与当前长期穿搭档案产生冲突。"""


class WardrobeItemNotFoundError(
    FashionAgentError,
):
    """当前用户不存在指定的衣橱单品。"""

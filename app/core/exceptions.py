class FashionAgentError(Exception):
    """Fashion-Agent 项目的基础异常。

    项目中自定义的异常都继承这个类，
    方便后续同意识别和处理项目内部错误。
    """


class ConfigurationError(FashionAgentError):
    """配置错误。
    
    当必要的环境变量缺失或配置值不合法时抛出。
    """

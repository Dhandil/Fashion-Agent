from app.core.exceptions import ConfigurationError, FashionAgentError


def test_configuration_error_inherits_project_error() -> None:
    """验证配置异常继承自项目基础异常。"""

    # issubclass 用于判断第一个类是否继承自第二个类
    assert issubclass(ConfigurationError, FashionAgentError)


def test_configuration_error_keeps_message() -> None:
    """验证异常对象能够保存错误消息。"""

    # 创建异常对象，但这里不主动抛出异常
    error = ConfigurationError("缺少必要配置")

    # str() 会取得创建异常时传入的消息
    assert str(error) == "缺少必要配置"

import logging


def setup_logging(log_level: str = "INFO") -> None:
    """
    初始化项目日志配置

    Args:
        log_level: 日志级别，例如DEBUG、INFO、WARNING、ERROR。
    """

    # 将日志级别转换为大写，允许传入 info、Info 等形式
    normalized_level = log_level.upper()

    # 根据级别名称获取 logging 对于的数字级别
    # 如果传入了无效值，默认使用 INFO
    numeric_level = getattr(logging, normalized_level, logging.INFO)

    # 设置整个应用的基础日志格式和输出级别
    logging.basicConfig(
        level=numeric_level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

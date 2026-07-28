import logging
from unittest.mock import patch

from app.core.logging import setup_logging


def test_setup_logging_uses_requested_level() -> None:
    """验证日志配置能够识别传入的日志级别。"""

    # 临时替换 logging.basicConfig，避免测试真正修改全局日志配置
    with patch("app.core.logging.logging.basicConfig") as mocked_basic_config:
        setup_logging("debug")

    # 验证 basicConfig 被调用了一次，并且参数符合预期
    mocked_basic_config.assert_called_once_with(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

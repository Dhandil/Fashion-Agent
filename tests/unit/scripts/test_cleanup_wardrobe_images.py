"""衣物图片清理命令测试。"""

import sys
from unittest.mock import patch

from scripts.cleanup_wardrobe_images import main


def test_cleanup_command_rejects_conflicting_modes() -> None:
    """验证预览和执行模式不能同时传入。"""

    with patch.object(
        sys,
        "argv",
        ["cleanup_wardrobe_images", "--dry-run", "--execute"],
    ):
        assert main() == 2

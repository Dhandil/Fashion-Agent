"""本地文件卷图片存储适配器测试。"""

from pathlib import Path

import pytest

from app.core.exceptions import WardrobeImageStorageError
from app.integrations.storage.local import LocalWardrobeImageStorage


def test_local_storage_writes_reads_and_deletes_bytes(tmp_path: Path) -> None:
    """验证图片字节可以写入、读取、判断存在并删除。"""

    storage = LocalWardrobeImageStorage(tmp_path / "uploads")
    content = b"fake-image-bytes"

    storage.write("asset/image.jpg", content)

    assert storage.exists("asset/image.jpg") is True
    assert storage.read("asset/image.jpg") == content

    storage.delete("asset/image.jpg")

    assert storage.exists("asset/image.jpg") is False


def test_local_storage_replaces_existing_object_atomically(tmp_path: Path) -> None:
    """验证重复写入同一对象键会替换旧内容，不留下临时文件。"""

    storage = LocalWardrobeImageStorage(tmp_path / "uploads")

    storage.write("asset/image.jpg", b"old")
    storage.write("asset/image.jpg", b"new")

    assert storage.read("asset/image.jpg") == b"new"
    assert list((tmp_path / "uploads" / "asset").glob("*.tmp")) == []


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    """验证对象键不能越过配置的文件卷根目录。"""

    storage = LocalWardrobeImageStorage(tmp_path / "uploads")

    with pytest.raises(WardrobeImageStorageError):
        storage.write("../outside.jpg", b"should-not-be-written")

    assert (tmp_path / "outside.jpg").exists() is False

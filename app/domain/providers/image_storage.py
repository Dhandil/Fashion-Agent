"""衣物图片对象存储能力协议。"""

from typing import Protocol


class WardrobeImageStorage(Protocol):
    """以对象键读写图片字节，业务层不依赖具体存储实现。"""

    def write(self, object_key: str, content: bytes) -> None:
        ...

    def read(self, object_key: str) -> bytes:
        ...

    def exists(self, object_key: str) -> bool:
        ...

    def delete(self, object_key: str) -> None:
        ...

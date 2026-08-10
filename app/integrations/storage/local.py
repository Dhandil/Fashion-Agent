"""本地文件卷衣物图片存储实现。"""

from pathlib import Path

from app.core.exceptions import WardrobeImageStorageError


class LocalWardrobeImageStorage:
    """将图片写入配置目录，并阻止对象键逃逸出根目录。"""

    def __init__(self, root_directory: str | Path) -> None:
        self._root = Path(root_directory).resolve()
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise WardrobeImageStorageError(
                "图片存储目录不可用，请检查文件卷权限。",
            ) from exc

    def _resolve(self, object_key: str) -> Path:
        path = (self._root / object_key).resolve()
        if self._root not in path.parents:
            raise WardrobeImageStorageError("图片对象路径无效。")
        return path

    def write(self, object_key: str, content: bytes) -> None:
        path = self._resolve(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        try:
            temporary_path.write_bytes(content)
            temporary_path.replace(path)
        except OSError as exc:
            raise WardrobeImageStorageError("图片写入失败，请稍后重试。") from exc

    def read(self, object_key: str) -> bytes:
        try:
            return self._resolve(object_key).read_bytes()
        except OSError as exc:
            raise WardrobeImageStorageError("图片读取失败，请稍后重试。") from exc

    def exists(self, object_key: str) -> bool:
        return self._resolve(object_key).is_file()

    def delete(self, object_key: str) -> None:
        path = self._resolve(object_key)
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            raise WardrobeImageStorageError("图片删除失败，请稍后重试。") from exc

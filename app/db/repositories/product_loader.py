from pathlib import Path

from pydantic import TypeAdapter

from app.domain.entities.product import Product


# 创建可重复使用的 Product 列表校验器
PRODUCT_LIST_ADAPTER = TypeAdapter(
    list[Product],
)


def load_products_from_json(
    file_path: Path,
) -> list[Product]:
    """从 JSON 文件加载并校验商品列表。"""

    # 使用 UTF-8 读取包含中文的商品文件
    json_content = file_path.read_text(
        encoding="utf-8",
    )

    # 将 JSON 字符串转换成 Product 实体列表
    return PRODUCT_LIST_ADAPTER.validate_json(
        json_content,
    )
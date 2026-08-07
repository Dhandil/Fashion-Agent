"""商品目录 API 数据结构。"""

from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    """商品搜索结果条目。"""

    product_id: str
    name: str
    category: str
    # 价格以字符串返回，避免浮点误差（例如 299.00）
    price: str
    currency: str
    colors: tuple[str, ...]
    sizes: tuple[str, ...]
    in_stock: bool


class ProductListResponse(BaseModel):
    """商品搜索结果。"""

    items: list[ProductResponse]
    count: int = Field(ge=0)
    total: int = Field(ge=0)

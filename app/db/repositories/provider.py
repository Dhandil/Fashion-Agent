"""商品仓库依赖提供模块。"""

from functools import lru_cache
from pathlib import Path

from app.db.repositories.in_memory_product import (
    InMemoryProductRepository,
)
from app.db.repositories.product_loader import (
    load_products_from_json,
)
from app.domain.repositories.product import ProductRepository


# 根据当前文件的位置，定位项目根目录下的商品数据文件
PRODUCT_DATA_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "samples"
    / "products.json"
)


@lru_cache
def get_product_repository() -> ProductRepository:
    """创建并缓存项目使用的商品仓库。"""

    # 从 JSON 文件中读取并验证商品数据
    products = load_products_from_json(PRODUCT_DATA_FILE)

    # 使用商品数据创建内存仓库
    return InMemoryProductRepository(products)
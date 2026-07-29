"""商品数据库模型与领域实体转换。"""

from app.db.models.product import ProductModel
from app.domain.entities.product import Product


def product_entity_to_model(
    product: Product,
) -> ProductModel:
    """将领域商品实体转换成数据库模型。"""

    return ProductModel(
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        price=product.price,
        currency=product.currency,
        # 领域实体使用只读元组，数据库 JSON 字段使用列表
        colors=list(product.colors),
        sizes=list(product.sizes),
        in_stock=product.in_stock,
    )


def product_model_to_entity(
    product_model: ProductModel,
) -> Product:
    """将数据库商品模型转换成领域实体。"""

    return Product(
        product_id=product_model.product_id,
        name=product_model.name,
        category=product_model.category,
        price=product_model.price,
        currency=product_model.currency,
        # Product 会将输入列表转换成领域层使用的元组
        colors=product_model.colors,
        sizes=product_model.sizes,
        in_stock=product_model.in_stock,
    )
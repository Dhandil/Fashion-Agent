"""商品目录 API 路由。"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.schemas.products import (
    ProductListResponse,
    ProductResponse,
)
from app.db.repositories.provider import (
    get_product_repository,
)
from app.domain.entities.product import Product
from app.domain.repositories.product import ProductRepository

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


def _to_response(product: Product) -> ProductResponse:
    """把商品领域实体映射为 API 响应。"""

    return ProductResponse(
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        price=str(product.price),
        currency=product.currency,
        colors=product.colors,
        sizes=product.sizes,
        in_stock=product.in_stock,
    )


@router.get(
    "",
    response_model=ProductListResponse,
    summary="搜索商品目录",
)
async def search_product_catalog(
    product_repository: Annotated[
        ProductRepository,
        Depends(get_product_repository),
    ],
    query: Annotated[
        str | None,
        Query(
            max_length=100,
            description="关键词，匹配商品名称或品类",
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(
            max_length=50,
            description="精确品类过滤",
        ),
    ] = None,
    max_price: Annotated[
        Decimal | None,
        Query(
            ge=0,
            description="最高价格（含），用于预算过滤",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=20,
            description="返回数量上限",
        ),
    ] = 5,
) -> ProductListResponse:
    """按关键词、品类和预算搜索有库存的商品目录。"""

    products = await product_repository.search(
        query=(query or "").strip(),
        category=category,
        max_price=max_price,
        limit=limit,
    )
    return ProductListResponse(
        items=[_to_response(product) for product in products],
        count=len(products),
        total=len(products),
    )

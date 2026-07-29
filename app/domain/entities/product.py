from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Product(BaseModel):
    """服装商品领域实体。"""

    # 商品唯一标识
    product_id: str

    # 商品名称
    name: str

    # 商品品类，例如衬衫、外套、长裤
    category: str

    # 商品价格，必须大于或等于0
    price: Decimal = Field(ge=0)

    # 货币代码，当前默认使用人民币
    currency: str = "CNY"

    # 商品可选颜色
    colors: tuple[str, ...] = ()

    # 商品可选尺码
    sizes: tuple[str, ...] = ()

    # 当前是否有库存
    in_stock: bool = True

    # 商品对象创建后不允许修改
    model_config = ConfigDict(frozen=True)
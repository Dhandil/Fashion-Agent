"""用户衣橱单品领域实体。"""

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class WardrobeItemStatus(StrEnum):
    """衣橱单品当前可用状态。"""

    # 当前可以参与穿搭推荐
    AVAILABLE = "available"

    # 正在清洗，暂时不能使用
    LAUNDRY = "laundry"

    # 因损坏、丢失等原因暂时不可使用
    UNAVAILABLE = "unavailable"


class WardrobeItem(BaseModel):
    """用户已经拥有的一件衣物或配饰。"""

    # 衣橱单品唯一标识
    wardrobe_item_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 所属用户，用于隔离不同用户的衣橱
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 用户容易识别的衣物名称
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    # 衣物品类，例如衬衫、长裤、鞋履或包
    category: str = Field(
        min_length=1,
        max_length=100,
    )

    # 品牌是可选信息，不强制用户提供
    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    # 一件衣物可能包含多个主要颜色
    colors: tuple[str, ...] = ()

    # 一件衣物可能由多种面料组成
    materials: tuple[str, ...] = ()

    # 尺码格式由具体品类决定，例如 M、42 或 170/88A
    size: str | None = Field(
        default=None,
        max_length=50,
    )

    # 风格标签，例如简约、复古或街头
    style_tags: tuple[str, ...] = ()

    # 适用季节，例如春季、夏季或四季
    seasons: tuple[str, ...] = ()

    # 适用场景，例如通勤、约会或运动
    scenarios: tuple[str, ...] = ()

    # 用户上传的衣物图片地址，当前暂时使用字符串保存
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 单品当前是否可以参与穿搭
    status: WardrobeItemStatus = (
        WardrobeItemStatus.AVAILABLE
    )

    # 用户主动提供的必要补充说明
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 领域对象创建后不能被原地修改
    model_config = ConfigDict(
        frozen=True,
    )
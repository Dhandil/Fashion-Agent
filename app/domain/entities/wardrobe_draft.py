"""衣物照片识别结果与待确认草稿领域实体。"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class WardrobeItemRecognition(BaseModel):
    """视觉模型对一张衣物照片的原始识别结果。

    模型只描述照片中可以看到的衣物特征，不包含用户身份、衣橱单品 ID
    和可用状态；额外字段会被直接忽略，避免模型伪造业务事实。
    """

    # 模型建议的衣物名称，无法辨认时留空
    name: str | None = None

    # 模型建议的衣物品类，无法辨认时留空
    category: str | None = None

    # 照片中可以观察到的主要颜色
    colors: tuple[str, ...] = ()

    # 只有面料特征明显时才给出，否则应留空
    materials: tuple[str, ...] = ()

    # 风格标签，例如简约、复古或街头
    style_tags: tuple[str, ...] = ()

    # 适用季节，例如春季、夏季或四季
    seasons: tuple[str, ...] = ()

    # 适用场景，例如通勤、约会或运动
    scenarios: tuple[str, ...] = ()

    # 模型自认为不确定、需要用户确认的字段名
    uncertain_fields: tuple[str, ...] = ()

    # 模型对本次识别结果的整体置信度
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
    )

    # 模型认为用户需要注意的补充说明
    notes: str | None = None

    # 忽略模型多输出的字段，避免 user_id 等身份信息进入领域对象
    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )


class WardrobeItemDraft(BaseModel):
    """由照片识别生成、等待用户确认的衣橱单品草稿。

    草稿只是候选信息。未经用户确认，草稿不能成为永久衣橱事实，
    因此这里不包含衣橱单品 ID、用户 ID 和可用状态。
    """

    # 草稿标识，仅用于同一次识别的客户端关联和问题排查
    draft_id: str = Field(
        min_length=1,
        max_length=100,
    )

    # 识别到的衣物名称；无法辨认时保持为空并进入 missing_fields
    name: str | None = Field(
        default=None,
        max_length=200,
    )

    # 识别到的衣物品类；无法辨认时保持为空并进入 missing_fields
    category: str | None = Field(
        default=None,
        max_length=100,
    )

    colors: tuple[str, ...] = ()
    materials: tuple[str, ...] = ()
    style_tags: tuple[str, ...] = ()
    seasons: tuple[str, ...] = ()
    scenarios: tuple[str, ...] = ()

    # 面向用户的补充说明，例如面料判断依据不足
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 客户端已经托管的照片地址；应用本身不保存照片字节
    image_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    # 新上传流程使用资产 ID 关联私有图片；旧 image_url 保持兼容
    image_asset_id: str | None = Field(
        default=None,
        max_length=100,
    )

    # 本次识别的整体置信度
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
    )

    # 已经识别但需要用户确认的字段
    uncertain_fields: tuple[str, ...] = ()

    # 照片无法确定、用户必须补充后才能创建衣物的字段
    missing_fields: tuple[str, ...] = ()

    # 照片本身无法可靠判断、只能由用户提供的字段
    unrecognizable_fields: tuple[str, ...] = ()

    # 草稿永远需要用户确认，不允许构造成自动写入的事实
    requires_confirmation: Literal[True] = True

    model_config = ConfigDict(
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_missing_fields(
        self,
    ) -> "WardrobeItemDraft":
        """保证空字段与 missing_fields 的说明保持一致。"""

        for field_name in (
            "name",
            "category",
        ):
            is_empty = getattr(self, field_name) is None
            is_reported = field_name in self.missing_fields

            if is_empty != is_reported:
                raise ValueError(
                    f"{field_name} 是否缺失必须与 missing_fields 保持一致",
                )

        # 同一字段不能既算已识别待确认，又算完全缺失
        overlapping_fields = set(self.uncertain_fields) & set(
            self.missing_fields,
        )
        if overlapping_fields:
            raise ValueError(
                "同一字段不能同时出现在 uncertain_fields 和 missing_fields",
            )

        return self

"""用户长期穿搭档案 API 路由。"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.style_profile import (
    PreferenceCandidateListResponse,
    PreferenceCandidateResponse,
    StyleProfileResponse,
    StyleProfileUpsertRequest,
)
from app.services.style_profile import (
    analyze_style_preference_candidates,
    get_style_profile,
    replace_style_profile,
)

router = APIRouter(
    prefix="/style-profile",
    tags=["style-profile"],
)


@router.get(
    "/candidates",
    response_model=PreferenceCandidateListResponse,
    summary="分析长期偏好候选",
)
async def list_preference_candidates(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    minimum_evidence: Annotated[
        int,
        Query(
            ge=2,
            le=20,
        ),
    ] = 2,
) -> PreferenceCandidateListResponse:
    """根据当前反馈动态分析风格偏好候选，不修改档案。"""

    candidates = await analyze_style_preference_candidates(
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        user_id=current_user.user_id,
        minimum_evidence=minimum_evidence,
    )
    response_items = tuple(
        PreferenceCandidateResponse.model_validate(
            candidate,
        )
        for candidate in candidates
    )

    return PreferenceCandidateListResponse(
        items=response_items,
        count=len(response_items),
        minimum_evidence=minimum_evidence,
    )


@router.get(
    "",
    response_model=StyleProfileResponse,
    summary="查询长期穿搭档案",
)
async def read_style_profile(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> StyleProfileResponse:
    """读取当前用户明确维护的长期穿搭偏好。"""

    profile = await get_style_profile(
        repository=repositories.style_profiles,
        user_id=current_user.user_id,
    )

    return StyleProfileResponse.model_validate(
        profile,
    )


@router.put(
    "",
    response_model=StyleProfileResponse,
    summary="新增或替换长期穿搭档案",
)
async def upsert_style_profile(
    request: StyleProfileUpsertRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> StyleProfileResponse:
    """使用当前用户明确确认的内容完整替换长期档案。"""

    profile = await replace_style_profile(
        repository=repositories.style_profiles,
        user_id=current_user.user_id,
        preferred_styles=request.preferred_styles,
        preferred_colors=request.preferred_colors,
        avoided_colors=request.avoided_colors,
        preferred_fits=request.preferred_fits,
        avoided_materials=request.avoided_materials,
        common_scenarios=request.common_scenarios,
        typical_budget_min=request.typical_budget_min,
        typical_budget_max=request.typical_budget_max,
        notes=request.notes,
    )

    return StyleProfileResponse.model_validate(
        profile,
    )

"""用户长期穿搭档案 API 路由。"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies.database import (
    FashionRepositoriesDependency,
)
from app.api.dependencies.identity import (
    CurrentUserDependency,
)
from app.api.schemas.style_profile import (
    PreferenceCandidateConfirmRequest,
    PreferenceCandidateListResponse,
    PreferenceCandidateResponse,
    PreferenceMemoryExpiryRequest,
    PreferenceMemoryListResponse,
    PreferenceMemoryResponse,
    StyleProfilePatchRequest,
    StyleProfileResponse,
    StyleProfileUpsertRequest,
)
from app.services.style_profile import (
    analyze_style_preference_candidates,
    confirm_style_preference_candidate,
    delete_preference_memory,
    delete_style_profile,
    get_style_profile,
    list_preference_memories,
    patch_style_profile,
    replace_style_profile,
    set_preference_memory_expiry,
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


@router.post(
    "/candidates/confirm",
    response_model=StyleProfileResponse,
    summary="确认长期偏好候选",
)
async def confirm_preference_candidate(
    request: PreferenceCandidateConfirmRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> StyleProfileResponse:
    """重新校验证据，并把用户确认的候选合并进长期档案。"""

    profile = await confirm_style_preference_candidate(
        style_profile_repository=(
            repositories.style_profiles
        ),
        outfit_repository=repositories.outfits,
        feedback_repository=(
            repositories.outfit_feedback
        ),
        preference_memory_repository=(
            repositories.preference_memories
        ),
        user_id=current_user.user_id,
        candidate_id=request.candidate_id,
        value=request.value,
        direction=request.direction,
        minimum_evidence=request.minimum_evidence,
    )

    return StyleProfileResponse.model_validate(
        profile,
    )


@router.get(
    "/memories",
    response_model=PreferenceMemoryListResponse,
    summary="查询长期偏好来源",
)
async def read_preference_memories(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    include_expired: bool = False,
) -> PreferenceMemoryListResponse:
    """读取当前用户已确认偏好的来源、证据和确认时间。"""

    memories = await list_preference_memories(
        repository=repositories.preference_memories,
        user_id=current_user.user_id,
        include_expired=include_expired,
    )
    items = tuple(
        PreferenceMemoryResponse.model_validate(memory)
        for memory in memories
    )
    return PreferenceMemoryListResponse(
        items=items,
        count=len(items),
        include_expired=include_expired,
    )


@router.patch(
    "/memories/{preference_memory_id}",
    response_model=PreferenceMemoryResponse,
    summary="设置长期偏好过期时间",
)
async def update_preference_memory_expiry(
    request: PreferenceMemoryExpiryRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    preference_memory_id: Annotated[
        str,
        Path(pattern=r"^pm_[0-9a-f]{32}$"),
    ],
) -> PreferenceMemoryResponse:
    """设置过期时间；显式传 null 可以恢复为长期有效。"""

    memory = await set_preference_memory_expiry(
        repository=repositories.preference_memories,
        user_id=current_user.user_id,
        preference_memory_id=preference_memory_id,
        expires_at=request.expires_at,
    )
    return PreferenceMemoryResponse.model_validate(memory)


@router.delete(
    "/memories/{preference_memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除一条长期偏好",
)
async def remove_preference_memory(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
    preference_memory_id: Annotated[
        str,
        Path(pattern=r"^pm_[0-9a-f]{32}$"),
    ],
) -> None:
    """删除偏好审计及其对档案的同向影响，并保持幂等。"""

    await delete_preference_memory(
        style_profile_repository=(
            repositories.style_profiles
        ),
        preference_memory_repository=(
            repositories.preference_memories
        ),
        user_id=current_user.user_id,
        preference_memory_id=preference_memory_id,
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
        avoided_styles=request.avoided_styles,
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


@router.patch(
    "",
    response_model=StyleProfileResponse,
    summary="部分更新长期穿搭档案",
)
async def update_style_profile(
    request: StyleProfilePatchRequest,
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> StyleProfileResponse:
    """只更新请求中明确提供的长期偏好字段。"""

    profile = await patch_style_profile(
        repository=repositories.style_profiles,
        user_id=current_user.user_id,
        changes=request.model_dump(
            exclude_unset=True,
        ),
    )

    return StyleProfileResponse.model_validate(
        profile,
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除长期穿搭档案",
)
async def remove_style_profile(
    current_user: CurrentUserDependency,
    repositories: FashionRepositoriesDependency,
) -> None:
    """删除当前用户的长期档案；档案不存在时也返回成功。"""

    await delete_style_profile(
        repository=repositories.style_profiles,
        preference_memory_repository=(
            repositories.preference_memories
        ),
        user_id=current_user.user_id,
    )

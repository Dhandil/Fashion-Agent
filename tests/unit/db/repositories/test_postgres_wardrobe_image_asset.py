"""PostgreSQL 衣物图片资产仓库测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wardrobe_image_asset import WardrobeImageAssetModel
from app.db.repositories.postgres_wardrobe_image_asset import (
    PostgresWardrobeImageAssetRepository,
)


@pytest.mark.anyio
async def test_list_cleanup_candidates_applies_lifecycle_filters() -> None:
    """验证清理查询同时覆盖过期、孤儿和待删除资产。"""

    session = AsyncMock(spec=AsyncSession)
    repository = PostgresWardrobeImageAssetRepository(session)
    scalar_result = Mock()
    scalar_result.all.return_value = []
    database_result = Mock()
    database_result.scalars.return_value = scalar_result
    session.execute.return_value = database_result

    now = datetime(2026, 8, 8, tzinfo=UTC)
    orphan_before = now - timedelta(days=1)
    deletion_before = now - timedelta(days=7)

    result = await repository.list_cleanup_candidates(
        now=now,
        orphan_uploaded_before=orphan_before,
        deletion_pending_before=deletion_before,
    )

    assert result == ()
    statement = session.execute.await_args.args[0]
    parameter_values = set(statement.compile().params.values())
    assert "pending" in parameter_values
    assert "uploaded" in parameter_values
    assert "deletion_pending" in parameter_values
    assert now in parameter_values
    assert orphan_before in parameter_values
    assert deletion_before in parameter_values


def test_image_asset_model_keeps_cleanup_columns() -> None:
    """验证图片资产模型包含清理服务所需的时间字段。"""

    columns = WardrobeImageAssetModel.__table__.columns

    assert "created_at" in columns
    assert "expires_at" in columns
    assert "attached_at" in columns
    assert "deleted_at" in columns

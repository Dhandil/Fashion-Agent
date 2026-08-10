"""清理本地衣物图片资产的命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import timedelta

from app.db.repositories.postgres_wardrobe_image_asset import (
    PostgresWardrobeImageAssetRepository,
)
from app.db.session import get_session_factory
from app.integrations.storage.provider import get_wardrobe_image_storage
from app.services.wardrobe_image_cleanup import (
    WardrobeImageCleanupResult,
    cleanup_wardrobe_image_assets,
)


def parse_args() -> argparse.Namespace:
    """解析清理模式和批量限制。"""

    parser = argparse.ArgumentParser(
        description="清理过期或孤儿衣物图片资产。默认只预览，不删除文件。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示候选数量，不删除文件或更新数据库（默认行为）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真正删除文件并将资产标记为 deleted",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        choices=range(1, 1001),
        metavar="N",
        help="本次最多处理的资产数量，默认 100",
    )
    return parser.parse_args()


async def run_cleanup(
    *,
    dry_run: bool,
    limit: int,
) -> WardrobeImageCleanupResult:
    """在单个数据库事务中执行一次清理批次。"""

    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = PostgresWardrobeImageAssetRepository(session)
        try:
            result = await cleanup_wardrobe_image_assets(
                repository,
                get_wardrobe_image_storage(),
                orphan_retention=timedelta(hours=24),
                deletion_retention=timedelta(days=7),
                limit=limit,
                dry_run=dry_run,
            )
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


def main() -> int:
    """执行清理并输出不包含用户信息的统计结果。"""

    args = parse_args()
    if args.dry_run and args.execute:
        print("--dry-run 和 --execute 不能同时使用。", file=sys.stderr)
        return 2

    dry_run = not args.execute
    try:
        result = asyncio.run(
            run_cleanup(
                dry_run=dry_run,
                limit=args.limit,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - CLI 边界需要将异常转换为退出码
        print(
            f"清理失败：{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    mode = "预览" if dry_run else "执行"
    print(
        f"[{mode}] 候选 {result.candidate_count}，"
        f"已删除 {result.deleted_count}，失败 {result.failed_count}",
    )
    return 0 if result.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

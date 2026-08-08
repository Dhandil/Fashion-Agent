import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Heart, ChevronLeft, ChevronRight } from "lucide-react";
import {
  useOutfitList,
  OUTFIT_PAGE_SIZE,
  type OutfitFilters,
} from "@/features/outfit/api";
import OutfitListCard from "@/features/outfit/OutfitListCard";
import OutfitDetailDrawer from "@/features/outfit/OutfitDetailDrawer";
import type { components } from "@/api/generated/schema";

type OutfitResponse = components["schemas"]["OutfitResponse"];

export default function OutfitsPage() {
  const qc = useQueryClient();

  const [filters, setFilters] = useState<OutfitFilters>({});
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<OutfitResponse | null>(null);

  const { data, isLoading, isError } = useOutfitList({
    ...filters,
    limit: OUTFIT_PAGE_SIZE,
    offset: page * OUTFIT_PAGE_SIZE,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / OUTFIT_PAGE_SIZE));

  // 列表刷新后同步详情抽屉，避免收藏状态继续使用旧对象。
  useEffect(() => {
    if (!selected) return;
    const refreshed = items.find((item) => item.outfit_id === selected.outfit_id);
    if (refreshed && refreshed !== selected) {
      setSelected(refreshed);
    }
  }, [items, selected]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 页面标题 */}
      <div className="px-16 md:px-32 pt-24 pb-16">
        <h1 className="text-h1 text-text-primary">我的穿搭</h1>
        <p className="text-small text-text-secondary mt-8">查看已保存、收藏和反馈过的穿搭方案。</p>
      </div>

      {/* 筛选栏 */}
      <div className="px-16 md:px-32 pb-16 flex flex-wrap items-center gap-8">
        <select
          value={filters.scenario ?? ""}
          onChange={(e) => {
            setFilters((f) => ({ ...f, scenario: e.target.value || null }));
            setPage(0);
          }}
          className="rounded-input border border-border bg-surface px-12 py-8 text-small text-text-primary outline-none focus:border-brand"
          aria-label="按场景筛选"
        >
          <option value="">全部场景</option>
          <option value="通勤">通勤</option>
          <option value="约会">约会</option>
          <option value="旅行">旅行</option>
          <option value="运动">运动</option>
          <option value="日常">日常</option>
        </select>
        <label className="inline-flex items-center gap-8 rounded-input border border-border bg-surface px-12 py-8 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.favorite_only ?? false}
            onChange={(e) => {
              setFilters((f) => ({ ...f, favorite_only: e.target.checked }));
              setPage(0);
            }}
            className="accent-brand"
          />
          <Heart size={14} className="text-danger" />
          <span className="text-small text-text-primary">仅看收藏</span>
        </label>
        <span className="text-caption text-text-secondary ml-auto">{total} 套</span>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto px-16 md:px-32 pb-24">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-16" aria-busy="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-card border border-border bg-surface p-16 space-y-12 animate-pulse">
                <div className="h-20 bg-surface-subtle rounded w-2/3" />
                <div className="h-12 bg-surface-subtle rounded w-1/3" />
                <div className="h-12 bg-surface-subtle rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-16">
            <p className="text-body text-danger">加载穿搭列表失败，请检查服务是否可用。</p>
            <button
              type="button"
              onClick={() => qc.invalidateQueries({ queryKey: ["outfits"] })}
              className="mt-12 px-16 py-8 rounded-input border border-border text-small hover:bg-surface-subtle"
            >
              重试
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="py-48 text-center space-y-16">
            <h2 className="text-h2 text-text-primary">
              {total === 0 ? "还没有保存过穿搭" : "没有符合条件的穿搭"}
            </h2>
            <p className="text-body text-text-secondary">
              {total === 0
                ? "在「智能搭配」中生成一套 Outfit 并保存，就会出现在这里。"
                : "试试调整筛选条件。"}
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-16">
              {items.map((outfit) => (
                <OutfitListCard
                  key={outfit.outfit_id}
                  outfit={outfit}
                  onClick={() => setSelected(outfit)}
                />
              ))}
            </div>

            {/* 分页 */}
            {pageCount > 1 && (
              <div className="flex items-center justify-center gap-16 pt-24">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="inline-flex items-center gap-4 px-12 py-8 rounded-input border border-border text-small
                             hover:bg-surface-subtle disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  aria-label="上一页"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-small text-text-secondary">
                  {page + 1} / {pageCount}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={page >= pageCount - 1}
                  className="inline-flex items-center gap-4 px-12 py-8 rounded-input border border-border text-small
                             hover:bg-surface-subtle disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  aria-label="下一页"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* 详情抽屉 */}
      {selected && (
        <OutfitDetailDrawer outfit={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

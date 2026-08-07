import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Camera, ChevronLeft, ChevronRight } from "lucide-react";
import {
  useWardrobeList,
  useCreateWardrobeItem,
  useUpdateWardrobeItem,
  useUpdateWardrobeStatus,
  useDeleteWardrobeItem,
  WARDROBE_PAGE_SIZE,
  type WardrobeFilters,
} from "@/features/wardrobe/api";
import WardrobeCard from "@/features/wardrobe/WardrobeCard";
import WardrobeFormDrawer, { type WardrobeFormValues } from "@/features/wardrobe/WardrobeFormDrawer";
import WardrobeImageRecognitionDrawer from "@/features/wardrobe/WardrobeImageRecognitionDrawer";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { isAppError, type AppError } from "@/api/client";
import type { components } from "@/api/generated/schema";

type WardrobeItem = components["schemas"]["WardrobeItemResponse"];

const CATEGORY_FILTERS = ["上装", "下装", "外套", "连衣裙", "鞋履", "配饰"];
const VISION_ENABLED = import.meta.env.VITE_ENABLE_WARDROBE_VISION === "true";

export default function WardrobePage() {
  const qc = useQueryClient();

  // 筛选与分页
  const [filters, setFilters] = useState<WardrobeFilters>({});
  const [page, setPage] = useState(0);

  // 抽屉与对话框状态
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [recognitionOpen, setRecognitionOpen] = useState(false);
  const [editItem, setEditItem] = useState<WardrobeItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WardrobeItem | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  // 数据
  const { data, isLoading, isError } = useWardrobeList({
    ...filters,
    limit: WARDROBE_PAGE_SIZE,
    offset: page * WARDROBE_PAGE_SIZE,
  });

  const createMutation = useCreateWardrobeItem();
  const updateMutation = useUpdateWardrobeItem(editItem?.wardrobe_item_id ?? "");
  const statusMutation = useUpdateWardrobeStatus();
  const deleteMutation = useDeleteWardrobeItem();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / WARDROBE_PAGE_SIZE));

  // ── 操作 ──

  const handleDrawerSubmit = useCallback(
    async (values: WardrobeFormValues) => {
      setPageError(null);
      try {
        if (editItem) {
          await updateMutation.mutateAsync(values);
        } else {
          await createMutation.mutateAsync(values);
        }
        setDrawerOpen(false);
        setEditItem(null);
      } catch (err) {
        const msg = isAppError(err) ? (err as AppError).message : "保存失败";
        setPageError(msg);
        throw err; // 让表单保持打开
      }
    },
    [createMutation, updateMutation, editItem],
  );

  const handleToggleStatus = useCallback(
    async (item: WardrobeItem) => {
      await statusMutation.mutateAsync({
        id: item.wardrobe_item_id,
        status: item.status === "available" ? "unavailable" : "available",
      });
    },
    [statusMutation],
  );

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.wardrobe_item_id);
      setDeleteTarget(null);
    } catch (err) {
      const msg = isAppError(err) ? (err as AppError).message : "删除失败";
      setPageError(msg);
      setDeleteTarget(null);
    }
  }, [deleteMutation, deleteTarget]);

  const clearUserCache = () => {
    qc.invalidateQueries({ queryKey: ["wardrobe"] });
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 页面标题 */}
      <div className="px-16 md:px-32 pt-24 pb-16 flex items-center justify-between flex-wrap gap-12">
        <div>
          <h1 className="text-h1 text-text-primary">我的衣橱</h1>
          <p className="text-small text-text-secondary mt-8">管理可以参与穿搭的衣物。</p>
        </div>
        <div className="flex gap-8">
          {VISION_ENABLED && (
            <button
              type="button"
              onClick={() => setRecognitionOpen(true)}
              className="inline-flex items-center gap-8 px-16 py-8 rounded-input border border-border
                         text-text-primary hover:bg-surface-subtle transition-colors"
            >
              <Camera size={16} />
              拍照识别
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setEditItem(null);
              setDrawerOpen(true);
            }}
            className="inline-flex items-center gap-8 px-16 py-8 rounded-input bg-brand text-surface
                       hover:bg-brand-hover transition-colors"
          >
            <Plus size={16} />
            新增衣物
          </button>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="px-16 md:px-32 pb-16 flex flex-wrap items-center gap-8">
        <select
          value={filters.category ?? ""}
          onChange={(e) => {
            setFilters((f) => ({ ...f, category: e.target.value || null }));
            setPage(0);
          }}
          className="rounded-input border border-border bg-surface px-12 py-8 text-small text-text-primary outline-none focus:border-brand"
          aria-label="按品类筛选"
        >
          <option value="">全部品类</option>
          {CATEGORY_FILTERS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          value={filters.status ?? ""}
          onChange={(e) => {
            setFilters((f) => ({
              ...f,
              status: (e.target.value as WardrobeFilters["status"]) || null,
            }));
            setPage(0);
          }}
          className="rounded-input border border-border bg-surface px-12 py-8 text-small text-text-primary outline-none focus:border-brand"
          aria-label="按状态筛选"
        >
          <option value="">全部状态</option>
          <option value="available">可用</option>
          <option value="unavailable">暂不可用</option>
        </select>
        <span className="text-caption text-text-secondary ml-auto">{total} 件</span>
      </div>

      {/* 错误提示 */}
      {pageError && (
        <div className="mx-16 md:mx-32 mb-16 rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12"
             role="alert">
          <p className="text-small text-danger">{pageError}</p>
        </div>
      )}

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto px-16 md:px-32 pb-24">
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-16" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-card border border-border bg-surface animate-pulse">
                <div className="aspect-[4/5] bg-surface-subtle" />
                <div className="p-12 space-y-8">
                  <div className="h-16 bg-surface-subtle rounded w-3/4" />
                  <div className="h-12 bg-surface-subtle rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-16">
            <p className="text-body text-danger">加载衣橱失败，请检查服务是否可用。</p>
            <button
              type="button"
              onClick={clearUserCache}
              className="mt-12 px-16 py-8 rounded-input border border-border text-small hover:bg-surface-subtle"
            >
              重试
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="py-48 text-center space-y-16">
            <h2 className="text-h2 text-text-primary">衣橱还是空的</h2>
            <p className="text-body text-text-secondary">
              先添加几件常穿衣物，Fashion-Agent 才能优先用已有衣服搭配。
            </p>
            <button
              type="button"
              onClick={() => {
                setEditItem(null);
                setDrawerOpen(true);
              }}
              className="inline-flex items-center gap-8 px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover transition-colors"
            >
              <Plus size={16} />
              新增第一件衣物
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-16">
              {items.map((item) => (
                <WardrobeCard
                  key={item.wardrobe_item_id}
                  item={item}
                  onEdit={() => {
                    setEditItem(item);
                    setDrawerOpen(true);
                  }}
                  onDelete={() => setDeleteTarget(item)}
                  onToggleStatus={() => handleToggleStatus(item)}
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

      {/* 新增/编辑抽屉 */}
      <WardrobeFormDrawer
        open={drawerOpen}
        mode={editItem ? "edit" : "create"}
        item={editItem}
        onClose={() => {
          setDrawerOpen(false);
          setEditItem(null);
        }}
        onSubmit={handleDrawerSubmit}
      />

      {/* 图片识别抽屉 */}
      <WardrobeImageRecognitionDrawer
        open={recognitionOpen}
        onClose={() => setRecognitionOpen(false)}
      />

      {/* 删除确认 */}
      {deleteTarget && (
        <ConfirmDialog
          title={`删除「${deleteTarget.name}」？`}
          description="删除后该衣物将不再出现在衣橱和穿搭推荐中。此操作无法撤销。"
          confirmLabel="删除衣物"
          busy={deleteMutation.isPending}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}

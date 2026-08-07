import { useState } from "react";
import { X, Search, Package, ExternalLink, Loader2 } from "lucide-react";
import { useProductSearch } from "@/features/outfit/api";

type Props = {
  open: boolean;
  /** 缺口角色，例如“鞋履”，作为初始搜索词 */
  gapRole?: string | null;
  onClose: () => void;
};

/** 辅助购物：商品搜索抽屉 · 报告第六阶段 MVP */
export default function ProductSearchDrawer({ open, gapRole, onClose }: Props) {
  const [query, setQuery] = useState(gapRole ?? "");
  const [category, setCategory] = useState("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [submitted, setSubmitted] = useState<{ query: string; category: string; maxPrice?: number } | null>(
    null,
  );

  if (!open) return null;

  const { data, isLoading, isError } = useProductSearch(
    {
      query: submitted?.query ?? (gapRole ?? undefined),
      category: submitted?.category || undefined,
      maxPrice: submitted?.maxPrice,
      limit: 10,
    },
    true,
  );

  const handleSearch = () => {
    setSubmitted({
      query: query.trim(),
      category: category.trim(),
      maxPrice: maxPrice.trim() ? Number(maxPrice.trim()) : undefined,
    });
  };

  const items = data?.items ?? [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-text-primary/40">
      <div className="w-full max-w-2xl h-full bg-canvas overflow-y-auto" role="dialog" aria-modal="true" aria-label="搜索商品">
        {/* 头部 */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-24 py-16 bg-surface border-b border-border">
          <h2 className="text-h2 text-text-primary">辅助购物 · 搜索商品</h2>
          <button type="button" onClick={onClose} className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle" aria-label="关闭">
            <X size={20} />
          </button>
        </div>

        <div className="p-24 space-y-20">
          {/* 搜索区 */}
          <div className="space-y-12">
            {gapRole && (
              <p className="text-small text-text-secondary">
                衣橱缺少：<span className="text-brand font-medium">{gapRole}</span>
              </p>
            )}
            <div className="flex gap-8">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={gapRole ? `搜索${gapRole}…` : "输入关键词，例如：衬衫"}
                aria-label="商品关键词"
                className="flex-1 rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand"
              />
              <button
                type="button"
                onClick={handleSearch}
                className="inline-flex items-center gap-8 px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover transition-colors"
              >
                <Search size={16} />
                搜索
              </button>
            </div>
            <div className="flex gap-8">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="rounded-input border border-border bg-surface px-12 py-8 text-small text-text-primary outline-none focus:border-brand"
                aria-label="品类筛选"
              >
                <option value="">全部品类</option>
                <option value="衬衫">衬衫</option>
                <option value="外套">外套</option>
                <option value="长裤">长裤</option>
                <option value="鞋履">鞋履</option>
              </select>
              <input
                type="number"
                min={0}
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                placeholder="最高价格（元）"
                aria-label="最高价格"
                className="w-32 rounded-input border border-border bg-surface px-12 py-8 text-small outline-none focus:border-brand"
              />
            </div>
          </div>

          {/* 状态与结果 */}
          {isLoading ? (
            <div className="flex items-center gap-8 rounded-card bg-surface-subtle px-16 py-12" aria-live="polite">
              <Loader2 size={18} className="text-brand animate-spin" />
              <span className="text-small text-text-secondary">搜索商品中…</span>
            </div>
          ) : isError ? (
            <div className="rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12" role="alert">
              <p className="text-small text-danger">搜索失败，请稍后重试。</p>
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-card border border-border bg-surface px-16 py-24 text-center">
              <Package size={28} className="mx-auto text-text-secondary mb-8" />
              <p className="text-body text-text-secondary">没有找到匹配的商品</p>
              <p className="text-small text-text-secondary mt-4">试试调整关键词、品类或价格范围。</p>
            </div>
          ) : (
            <ul className="space-y-12" role="list">
              {items.map((p) => (
                <li key={p.product_id} className="rounded-card border border-border bg-surface p-16 space-y-8">
                  <div className="flex items-start justify-between gap-8">
                    <div>
                      <h3 className="text-body font-medium text-text-primary">{p.name}</h3>
                      <p className="text-caption text-text-secondary mt-4">{p.category}</p>
                    </div>
                    <span className="text-body font-medium text-brand">{p.price} {p.currency}</span>
                  </div>
                  {(p.colors.length > 0 || p.sizes.length > 0) && (
                    <p className="text-caption text-text-secondary">
                      {[p.colors.join("、"), p.sizes.join("、")].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  <div className="flex items-center justify-between">
                    <span className={`text-caption ${p.in_stock ? "text-success" : "text-text-secondary"}`}>
                      {p.in_stock ? "有货" : "缺货"}
                    </span>
                    <span className="inline-flex items-center gap-4 text-caption text-text-secondary">
                      <ExternalLink size={12} />
                      来源链接即将支持
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

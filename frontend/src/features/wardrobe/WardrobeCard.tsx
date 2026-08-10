import type { components } from "@/api/generated/schema";
import { useWardrobeImageUrl } from "@/features/wardrobe/api";
import { Shirt, MoreVertical, Pencil, Trash2, ToggleLeft, ToggleRight } from "lucide-react";

type WardrobeItem = components["schemas"]["WardrobeItemResponse"];

type Props = {
  item: WardrobeItem;
  onEdit: () => void;
  onDelete: () => void;
  onToggleStatus: () => void;
};

export default function WardrobeCard({ item, onEdit, onDelete, onToggleStatus }: Props) {
  const isAvailable = item.status === "available";
  const imageSource = item.image_url ?? (
    item.image_asset_id
      ? `/api/v1/wardrobe/images/${encodeURIComponent(item.image_asset_id)}/content`
      : null
  );
  const { resolvedUrl, isLoading: imageLoading } = useWardrobeImageUrl(imageSource);

  return (
    <div className="soft-card soft-card-hover group overflow-hidden flex flex-col">
      {/* 图片区 */}
      <div className="relative aspect-[4/5] bg-surface-subtle flex items-center justify-center overflow-hidden">
        <span className="absolute left-10 top-10 z-[1] rounded-tag bg-surface/90 px-8 py-2 text-[0.62rem] font-medium tracking-wide text-brand shadow-sm backdrop-blur-sm">
          {item.category}
        </span>
        {imageLoading ? (
          <div className="w-full h-full bg-surface-subtle animate-pulse" aria-label="正在加载图片" />
        ) : resolvedUrl ? (
          <img
            src={resolvedUrl}
            alt={item.name}
            loading="lazy"
            className={`h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02] ${isAvailable ? "" : "grayscale opacity-60"}`}
          />
        ) : (
          <div className="flex flex-col items-center gap-8 text-text-secondary">
            <Shirt size={40} strokeWidth={1.5} />
            <span className="text-caption">{item.category}</span>
          </div>
        )}
      </div>

      {/* 信息区 */}
      <div className="flex flex-1 flex-col gap-4 p-16">
        <div className="flex items-start justify-between gap-8">
          <div className="min-w-0">
            <h3 className="text-body font-medium text-text-primary truncate">{item.name}</h3>
            <p className="text-small text-text-secondary mt-2">
              {[item.colors[0], item.size].filter(Boolean).join(" · ") || item.category}
            </p>
          </div>
          <div className="relative group">
            <button
              type="button"
              className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle"
              aria-label={`${item.name} 更多操作`}
            >
              <MoreVertical size={18} />
            </button>
            <div className="hidden group-hover:flex group-focus-within:flex flex-col absolute right-0 top-full z-10 mt-4
                            rounded-card border border-border bg-surface shadow-md min-w-32 py-8">
              <button
                type="button"
                onClick={onEdit}
                className="flex items-center gap-8 px-12 py-8 text-small text-text-primary hover:bg-surface-subtle"
              >
                <Pencil size={14} /> 编辑
              </button>
              <button
                type="button"
                onClick={onToggleStatus}
                className="flex items-center gap-8 px-12 py-8 text-small text-text-primary hover:bg-surface-subtle"
              >
                {isAvailable ? <ToggleLeft size={14} /> : <ToggleRight size={14} />}
                {isAvailable ? "标记不可用" : "标记可用"}
              </button>
              <button
                type="button"
                onClick={onDelete}
                className="flex items-center gap-8 px-12 py-8 text-small text-danger hover:bg-danger/5"
              >
                <Trash2 size={14} /> 删除
              </button>
            </div>
          </div>
        </div>

        {/* 状态 */}
        <div className="flex items-center gap-6 mt-auto pt-4">
          <span
            className={`inline-block w-8 h-8 rounded-full ${
              isAvailable ? "bg-success" : "bg-text-secondary"
            }`}
            aria-hidden="true"
          />
          <span className={`text-small ${isAvailable ? "status-available" : "status-unavailable"}`}>
            {isAvailable ? "可用" : "暂不可用"}
          </span>
        </div>
      </div>
    </div>
  );
}

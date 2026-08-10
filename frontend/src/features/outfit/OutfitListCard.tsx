import type { components } from "@/api/generated/schema";
import { Heart, Shirt } from "lucide-react";
import SourceTag from "@/features/outfit/SourceTag";

type OutfitResponse = components["schemas"]["OutfitResponse"];

type Props = {
  outfit: OutfitResponse;
  onClick: () => void;
};

/** 已保存 Outfit 列表卡片 · ui-design §8.1 */
export default function OutfitListCard({ outfit, onClick }: Props) {
  // 核心单品摘要（前 3 件）
  const coreItems = outfit.items.slice(0, 3);

  return (
    <button
      type="button"
      onClick={onClick}
      className="soft-card soft-card-hover group w-full space-y-12 p-20 text-left"
    >
      {/* 标题行 */}
      <div className="flex items-start justify-between gap-8">
        <h3 className="text-body font-medium text-text-primary group-hover:text-brand transition-colors">
          {outfit.name}
        </h3>
        {outfit.is_favorite && (
          <Heart size={16} className="text-danger fill-danger shrink-0" aria-label="已收藏" />
        )}
      </div>

      {/* 元信息 */}
      <div className="flex flex-wrap gap-8">
        {outfit.scenario && (
          <span className="inline-flex items-center rounded-tag bg-surface-subtle px-8 py-2 text-caption text-text-secondary">
            {outfit.scenario}
          </span>
        )}
        {outfit.season && (
          <span className="inline-flex items-center rounded-tag bg-surface-subtle px-8 py-2 text-caption text-text-secondary">
            {outfit.season}
          </span>
        )}
        {outfit.style_tags.slice(0, 2).map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center rounded-tag bg-surface-subtle px-8 py-2 text-caption text-text-secondary"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* 单品摘要 */}
      <div className="space-y-4 pt-4">
        {coreItems.map((item, i) => (
          <div key={i} className="flex items-center gap-8 text-small">
            <Shirt size={14} className="text-text-secondary shrink-0" aria-hidden="true" />
            <span className="text-text-primary truncate">{item.name}</span>
            <SourceTag source={item.source} />
          </div>
        ))}
        {outfit.items.length > coreItems.length && (
          <p className="text-caption text-text-secondary pl-22">
            +{outfit.items.length - coreItems.length} 件单品
          </p>
        )}
      </div>
    </button>
  );
}

import type { components } from "@/api/generated/schema";
import { Bookmark, Shirt } from "lucide-react";
import SourceTag from "./SourceTag";

type OutfitRecommendation = components["schemas"]["OutfitRecommendation"];

type Props = {
  outfit: OutfitRecommendation;
  onSave: () => void;
  saving: boolean;
};

export default function OutfitCard({ outfit, onSave, saving }: Props) {
  return (
    <div className="rounded-card-lg border border-border bg-surface p-20 md:p-24 space-y-16">
      {/* 头部：名称 + 场景/风格 */}
      <div className="space-y-8">
        <h3 className="text-h3 text-text-primary">{outfit.name}</h3>
        <div className="flex flex-wrap gap-8">
          {outfit.scenario && (
            <span className="inline-flex items-center rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary">
              {outfit.scenario}
            </span>
          )}
          {outfit.season && (
            <span className="inline-flex items-center rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary">
              {outfit.season}
            </span>
          )}
          {outfit.style_tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* 单品列表 */}
      <ul className="space-y-10" role="list">
        {outfit.items.map((item, i) => (
          <li key={i} className="flex items-start gap-12">
            <div className="flex items-center justify-center w-32 h-32 rounded-input bg-surface-subtle shrink-0 mt-2">
              <Shirt size={16} className="text-text-secondary" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-8 flex-wrap">
                <span className="text-body font-medium text-text-primary">{item.name}</span>
                <SourceTag source={item.source} />
              </div>
              <p className="text-caption text-text-secondary mt-2">{item.role}</p>
              {item.reason && (
                <p className="text-small text-text-secondary mt-4">{item.reason}</p>
              )}
            </div>
          </li>
        ))}
      </ul>

      {/* 推荐理由 */}
      <div className="border-t border-border pt-12">
        <p className="text-body text-text-primary leading-relaxed">
          {outfit.recommendation_reason}
        </p>
      </div>

      {/* 替代单品 */}
      {outfit.alternatives.length > 0 && (
        <details className="group">
          <summary className="text-small text-text-secondary cursor-pointer hover:text-text-primary transition-colors">
            查看 {outfit.alternatives.length} 个替代单品
          </summary>
          <ul className="mt-8 space-y-6 pl-16" role="list">
            {outfit.alternatives.map((alt, i) => (
              <li key={i} className="text-small text-text-secondary">
                {alt.name} · {alt.role}
                <SourceTag source={alt.source} />
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* 注意事项 */}
      {outfit.notes && (
        <div className="rounded-card bg-warning/10 border border-warning/20 px-12 py-8">
          <p className="text-small text-warning">{outfit.notes}</p>
        </div>
      )}

      {/* 保存按钮 */}
      <div className="pt-8">
        <button
          onClick={onSave}
          disabled={saving}
          className="inline-flex items-center gap-8 rounded-input bg-brand px-16 py-8 text-body text-surface
                     hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Bookmark size={18} />
          {saving ? "保存中…" : "保存这套穿搭"}
        </button>
      </div>
    </div>
  );
}

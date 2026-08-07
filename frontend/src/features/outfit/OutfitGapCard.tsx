import { useState } from "react";
import type { components } from "@/api/generated/schema";
import ProductSearchDrawer from "@/features/outfit/ProductSearchDrawer";

type OutfitGapReport = components["schemas"]["OutfitGapReport"];

type Props = { gap: OutfitGapReport };

const GAP_ACTION_LABELS: Record<string, string> = {
  add_wardrobe_items: "去衣橱补充",
  adjust_requirements: "调整要求",
  search_products: "搜索商品",
};

export default function OutfitGapCard({ gap }: Props) {
  const [searchOpen, setSearchOpen] = useState(false);

  // 允许购物时给出第一个缺口的角色作为初始搜索词
  const searchRole = gap.gaps[0]?.role ?? null;
  const canSearch = gap.shopping_search_allowed;

  return (
    <div className="rounded-card-lg border border-warning/30 bg-warning/[0.04] p-20 md:p-24 space-y-16">
      <h3 className="text-h3 text-text-primary">
        还缺少 {gap.missing_roles.length} 个核心单品
      </h3>

      {/* 缺口明细 */}
      <ul className="space-y-12" role="list">
        {gap.gaps.map((g, i) => (
          <li key={i} className="text-body text-text-primary">
            <span className="font-medium">{g.role ?? gap.missing_roles[i]}</span>
            {g.reason && (
              <span className="text-text-secondary"> — {g.reason}</span>
            )}
          </li>
        ))}
      </ul>

      {/* 原因 */}
      {gap.reason && (
        <p className="text-small text-text-secondary">{gap.reason}</p>
      )}

      {/* 下一步：搜索商品已接通；其余为说明标签 */}
      {gap.next_actions.length > 0 && (
        <div className="flex flex-wrap gap-8 pt-4">
          {gap.next_actions
            .filter((a) => a !== "search_products" || canSearch)
            .map((action) =>
              action === "search_products" && canSearch ? (
                <button
                  key={action}
                  type="button"
                  onClick={() => setSearchOpen(true)}
                  className="inline-flex items-center rounded-tag bg-brand px-12 py-6 text-small text-surface
                             hover:bg-brand-hover transition-colors"
                >
                  {GAP_ACTION_LABELS[action] ?? action}
                </button>
              ) : (
                <span
                  key={action}
                  className="inline-flex items-center rounded-tag border border-border px-12 py-6
                             text-small text-text-secondary"
                  title="该入口即将支持"
                >
                  {GAP_ACTION_LABELS[action] ?? action} · 即将支持
                </span>
              ),
            )}
        </div>
      )}

      {/* 商品搜索抽屉 */}
      <ProductSearchDrawer
        open={searchOpen}
        gapRole={searchRole}
        onClose={() => setSearchOpen(false)}
      />
    </div>
  );
}

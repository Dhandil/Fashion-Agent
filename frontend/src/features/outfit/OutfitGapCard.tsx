import type { components } from "@/api/generated/schema";

type OutfitGapReport = components["schemas"]["OutfitGapReport"];

type Props = { gap: OutfitGapReport };

const GAP_ACTION_LABELS: Record<string, string> = {
  add_wardrobe_items: "去衣橱补充",
  adjust_requirements: "调整要求",
  search_products: "帮我搜索商品",
};

export default function OutfitGapCard({ gap }: Props) {
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

      {/* 下一步（当前为说明标签，后续接入实际流程） */}
      {gap.next_actions.length > 0 && (
        <div className="flex flex-wrap gap-8 pt-4">
          {/* 只有 shopping_search_allowed 时才显示搜商品入口 */}
          {gap.next_actions
            .filter((a) => a !== "search_products" || gap.shopping_search_allowed)
            .map((action) => (
              <span
                key={action}
                className="inline-flex items-center rounded-tag border border-border px-12 py-6
                           text-small text-text-secondary"
                title="该入口即将支持"
              >
                {GAP_ACTION_LABELS[action] ?? action} · 即将支持
              </span>
            ))}
        </div>
      )}
    </div>
  );
}

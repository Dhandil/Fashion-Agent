import type { components } from "@/api/generated/schema";

type Source = components["schemas"]["OutfitItemSource"];

const SOURCE_CONFIG: Record<Source, { label: string; className: string }> = {
  wardrobe: { label: "我的衣橱", className: "source-tag-wardrobe" },
  product: { label: "外部商品", className: "source-tag-product" },
  recommendation: { label: "建议单品", className: "source-tag-recommendation" },
};

export default function SourceTag({ source }: { source: Source }) {
  const cfg = SOURCE_CONFIG[source];
  return <span className={cfg.className}>{cfg.label}</span>;
}

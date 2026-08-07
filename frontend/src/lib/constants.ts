/** 来自 visual-direction §5.1 · 导航顺序 */
export const NAV_ITEMS = [
  { to: "/", label: "智能搭配", icon: "MessageSquare" },
  { to: "/wardrobe", label: "我的衣橱", icon: "Shirt" },
  { to: "/outfits", label: "我的穿搭", icon: "LayoutGrid" },
  { to: "/profile", label: "风格档案", icon: "UserRound" },
  { to: "/settings", label: "设置", icon: "Settings" },
] as const;

/** 来自 frontend §2 · 产品核心任务 */
export const APP_DESCRIPTION =
  "先帮你决定怎么穿，再判断是否需要买。AI 穿搭与衣橱助手。";

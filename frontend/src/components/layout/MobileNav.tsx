import { NavLink, useLocation } from "react-router-dom";
import { NAV_ITEMS } from "@/lib/constants";
import { NAV_ICONS } from "@/lib/icons";

/** 移动端底部导航 · 只显示前 4 项（搭配/衣橱/穿搭/我的），设置作为"我的"二级入口 */
const MOBILE_ITEMS = NAV_ITEMS.slice(0, 4);

export default function MobileNav() {
  const location = useLocation();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 border-t border-border/80 bg-surface/95 backdrop-blur-md safe-area-bottom md:hidden"
      aria-label="主导航"
    >
      <ul className="flex justify-around py-8" role="list">
        {MOBILE_ITEMS.map((item) => {
          const isActive =
            item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
          const Icon = NAV_ICONS[item.icon];
          return (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={`relative flex flex-col items-center gap-2 rounded-card px-12 py-4 text-caption transition-all touch-target
                  ${isActive ? "bg-brand/[0.08] text-brand font-medium" : "text-text-secondary"}`}
              >
                {isActive && (
                  <span className="absolute -top-4 h-4 w-20 rounded-tag bg-accent" aria-hidden="true" />
                )}
                {Icon && <Icon size={20} aria-hidden="true" />}
                <span>{item.label}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

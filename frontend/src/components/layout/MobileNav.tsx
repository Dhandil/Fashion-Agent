import { NavLink, useLocation } from "react-router-dom";
import { NAV_ITEMS } from "@/lib/constants";
import { NAV_ICONS } from "@/lib/icons";

/** 移动端底部导航 · 只显示前 4 项（搭配/衣橱/穿搭/我的），设置作为"我的"二级入口 */
const MOBILE_ITEMS = NAV_ITEMS.slice(0, 4);

export default function MobileNav() {
  const location = useLocation();

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 bg-surface border-t border-border safe-area-bottom"
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
                className={`flex flex-col items-center gap-2 px-12 py-4 text-caption transition-colors touch-target
                  ${isActive ? "text-brand font-medium" : "text-text-secondary"}`}
              >
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

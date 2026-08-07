import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "@/lib/constants";
import { NAV_ICONS } from "@/lib/icons";

export default function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-sidebar shrink-0 bg-surface border-r border-border">
      {/* 品牌标识 */}
      <div className="h-64 flex items-center px-16">
        <span className="text-h2 text-brand font-semibold">Fashion-Agent</span>
      </div>

      {/* 导航 */}
      <nav className="flex-1 px-12 py-8">
        <ul className="space-y-4" role="list">
          {NAV_ITEMS.map((item) => {
            const Icon = NAV_ICONS[item.icon];
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-12 px-12 py-8 rounded-input text-body transition-colors
                    ${isActive
                      ? "bg-brand/10 text-brand font-medium"
                      : "text-text-secondary hover:bg-surface-subtle hover:text-text-primary"
                    }`
                  }
                >
                  {Icon && <Icon size={20} aria-hidden="true" />}
                  {item.label}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* 底部版本 */}
      <div className="px-16 py-12 text-caption text-text-secondary">
        v0.1
      </div>
    </aside>
  );
}

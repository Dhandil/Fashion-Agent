import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "@/lib/constants";
import { NAV_ICONS } from "@/lib/icons";

export default function Sidebar() {
  return (
    <aside className="hidden w-[17rem] shrink-0 flex-col border-r border-border/80 bg-surface/90 backdrop-blur-sm md:flex">
      {/* 像衣物吊牌一样的品牌标识，建立个人衣橱辨识度。 */}
      <div className="px-16 pb-20 pt-20">
        <div className="closet-label flex items-center gap-10 px-24 py-12">
          <span className="relative flex h-36 w-36 items-center justify-center rounded-card bg-brand text-h3 font-semibold text-surface">
            FA
            <span className="absolute -right-3 -top-3 h-8 w-8 rotate-12 rounded-sm border-2 border-surface bg-accent" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <span className="block truncate text-body font-semibold tracking-tight text-text-primary">Fashion-Agent</span>
            <span className="text-caption text-text-secondary">我的衣橱 · 我的搭配</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-12 py-8" aria-label="主导航">
        <p className="px-12 pb-10 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-brand/65">
          My closet
        </p>
        <ul className="space-y-8" role="list">
          {NAV_ITEMS.map((item, index) => {
            const Icon = NAV_ICONS[item.icon];
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `group relative flex min-h-[54px] items-center gap-12 overflow-hidden rounded-card px-14 py-12 text-body transition-all
                    ${isActive
                      ? "bg-brand text-surface font-medium shadow-[0_10px_24px_rgba(72,86,200,0.22)]"
                      : "text-text-secondary hover:bg-surface-subtle hover:text-text-primary"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={`absolute inset-y-10 left-0 w-3 rounded-r-tag ${isActive ? "bg-accent" : "bg-transparent"}`}
                        aria-hidden="true"
                      />
                      {Icon && <Icon size={22} strokeWidth={1.8} aria-hidden="true" />}
                      <span>{item.label}</span>
                      <span className="ml-auto text-[0.62rem] tracking-[0.14em] opacity-55" aria-hidden="true">
                        0{index + 1}
                      </span>
                    </>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="px-16 pb-20 pt-12">
        <div className="flex items-center justify-between rounded-card border border-dashed border-border bg-canvas/80 px-12 py-10 text-caption text-text-secondary">
          <span className="inline-flex items-center gap-6">
            <span className="h-6 w-6 rounded-full bg-success" aria-hidden="true" />
            私人衣橱已连接
          </span>
          <span>v0.1</span>
        </div>
      </div>
    </aside>
  );
}

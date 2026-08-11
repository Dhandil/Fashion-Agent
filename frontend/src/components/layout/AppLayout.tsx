import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";

export default function AppLayout() {
  return (
    <div className="flex h-dvh overflow-hidden">
      {/* 桌面侧栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <main className="relative flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-y-auto pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* 移动端底部导航 */}
      <MobileNav />
    </div>
  );
}

import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";

export default function AppLayout() {
  return (
    <div className="flex min-h-dvh overflow-hidden">
      {/* 桌面侧栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <main className="relative flex-1 flex flex-col min-w-0 overflow-y-auto pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* 移动端底部导航 */}
      <MobileNav />
    </div>
  );
}

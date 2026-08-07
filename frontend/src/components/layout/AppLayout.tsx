import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* 桌面侧栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Outlet />
      </main>

      {/* 移动端底部导航 */}
      <MobileNav />
    </div>
  );
}

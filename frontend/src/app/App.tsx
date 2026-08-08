import { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { onUserChange } from "@/api/client";
import { useChatStore } from "@/stores/chat";
import AppRoutes from "@/routes";

// 服务端状态缓存 · frontend §9
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  // 用户身份变化时清空全部缓存，避免不同用户的数据串用
  useEffect(() => {
    return onUserChange(() => {
      queryClient.clear();
      // 同时清理进程内聊天状态，避免身份切换后继续显示上一位用户的消息。
      useChatStore.getState().endSession();
    });
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

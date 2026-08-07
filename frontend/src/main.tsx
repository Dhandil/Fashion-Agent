import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setUserId } from "@/api/client";
import "@/styles/globals.css";
import App from "@/app/App";

// 用户身份初始化
// - 任意环境：优先使用构建时注入的 VITE_DEV_USER_ID（演示/开发部署）
// - 本地开发：无配置时兜底 dev-user-001
// - 真实生产：不注入该变量，等待接入 JWT/OAuth 可信认证
const configuredUserId = import.meta.env.VITE_DEV_USER_ID;
if (configuredUserId) {
  setUserId(configuredUserId);
} else if (import.meta.env.DEV) {
  setUserId("dev-user-001");
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

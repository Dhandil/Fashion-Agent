import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setUserId } from "@/api/client";
import "@/styles/globals.css";
import App from "@/app/App";

// 开发环境临时用户身份 · 生产必须接入可信认证（JWT/OAuth），禁用伪身份
if (import.meta.env.DEV) {
  const devUserId = import.meta.env.VITE_DEV_USER_ID ?? "dev-user-001";
  setUserId(devUserId);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

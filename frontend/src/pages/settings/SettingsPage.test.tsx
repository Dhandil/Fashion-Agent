import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import SettingsPage from "./SettingsPage";
import { setUserId } from "@/api/client";

setUserId("test-user");

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SettingsPage", () => {
  it("健康检查成功时显示运行正常与服务信息", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            app_name: "Fashion-Agent",
            environment: "development",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(<SettingsPage />, { wrapper });

    expect(await screen.findByText(/运行正常/)).toBeInTheDocument();
    expect(screen.getByText(/Fashion-Agent/)).toBeInTheDocument();
    expect(screen.getByText(/development/)).toBeInTheDocument();
  });

  it("健康检查失败时显示错误与重试按钮", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("network down")),
    );

    render(<SettingsPage />, { wrapper });

    expect(await screen.findByText(/网络连接失败/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /重试/ })).toBeInTheDocument();
  });

  it("提供清除个人档案入口", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            app_name: "Fashion-Agent",
            environment: "development",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(<SettingsPage />, { wrapper });

    expect(
      await screen.findByRole("button", { name: /清除个人档案/ }),
    ).toBeInTheDocument();
  });
});

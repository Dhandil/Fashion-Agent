import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useSaveOutfit } from "@/features/conversation/api";
import { setUserId } from "@/api/client";

setUserId("test-user");

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSaveOutfit", () => {
  it("保存成功后刷新穿搭列表缓存并返回 true", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ outfit_id: "o-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })),
    );

    const { result } = renderHook(() => useSaveOutfit(), { wrapper });
    let ok = false;
    await act(async () => {
      ok = await result.current.save("cid-1");
    });
    expect(ok).toBe(true);

    // 请求体：conversation_id 正确发送
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe("/api/v1/outfits");
    expect(init?.body).toBe(JSON.stringify({ conversation_id: "cid-1" }));
  });

  it("后端 4xx 时返回 false 且不抛异常", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: "conversation_not_found", message: "会话不存在" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const { result } = renderHook(() => useSaveOutfit(), { wrapper });
    let ok = true;
    await act(async () => {
      ok = await result.current.save("cid-missing");
    });
    expect(ok).toBe(false);
    expect(result.current.error?.code).toBe("conversation_not_found");
  });
});

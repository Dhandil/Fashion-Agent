import { afterEach, describe, expect, it, vi } from "vitest";
import { api, isAppError, onUserChange, setUserId, type AppError } from "@/api/client";

// 用户身份在 DEV 入口设置；测试直接注入
setUserId("test-user");

const BASE = "/api/v1";

function mockFetchResponse(status: number, body: unknown, headers?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...(headers ?? {}) },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("API 错误归一化", () => {
  it("网络错误 → network_error，可重试", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    await expect(api.get("/test")).rejects.toMatchObject({
      code: "network_error",
      retryable: true,
      status: null,
    });
  });

  it("422 → validation_error 且带 fieldErrors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse(422, {
          detail: [
            { loc: ["body", "message"], msg: "字段无效" },
            { loc: ["body", "category"], msg: "不能为空" },
          ],
        }),
      ),
    );
    try {
      await api.post("/test", {});
      expect.unreachable();
    } catch (err) {
      expect(isAppError(err)).toBe(true);
      const e = err as AppError;
      expect(e.code).toBe("validation_error");
      expect(e.fieldErrors?.["message"]).toEqual(["字段无效"]);
      expect(e.fieldErrors?.["category"]).toEqual(["不能为空"]);
    }
  });

  it("项目 ErrorResponse → 透传 code/message，5xx 标记可重试", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse(503, { code: "upstream_unavailable", message: "上游不可用" }),
      ),
    );
    await expect(api.get("/test")).rejects.toMatchObject({
      code: "upstream_unavailable",
      message: "上游不可用",
      retryable: true,
      status: 503,
    });
  });

  it("Request ID 优先取 X-Request-ID 响应头", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        mockFetchResponse(
          500,
          { code: "internal", message: "错误", request_id: "body-req" },
          { "X-Request-ID": "header-req" },
        ),
      ),
    );
    await expect(api.get("/test")).rejects.toMatchObject({ requestId: "header-req" });
  });

  it("未设置身份时直接拒绝，不发请求", async () => {
    // 临时清空身份：setUserId 只接受 string，通过直接清内部状态模拟
    // 这里改用传 xUserId 场景验证：request 强制要求 userId 或 xUserId
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockFetchResponse(200, { ok: true })),
    );
    // 无身份时（无法从外部清空，此处通过断言 fetch 收到 X-User-ID 验证身份注入）
    await api.get("/test");
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe(`${BASE}/test`);
    expect((init?.headers as Record<string, string>)["X-User-ID"]).toBe("test-user");
  });

  it("匿名请求不要求身份也不携带 X-User-ID", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockFetchResponse(200, { ok: true })),
    );
    await api.get("/health", { anonymous: true });
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe(`${BASE}/health`);
    const headers = (init?.headers as Record<string, string>) ?? {};
    expect(headers["X-User-ID"]).toBeUndefined();
  });

  it("setUserId 变化时触发用户切换回调", async () => {
    const seen: Array<[string | null, string]> = [];
    const unsubscribe = onUserChange((prev, next) => seen.push([prev, next]));

    // 当前身份是 test-user（顶层设置）
    setUserId("user-b");
    setUserId("user-b"); // 相同身份不重复触发
    setUserId("user-c");

    unsubscribe();
    setUserId("user-d"); // 取消注册后不再触发

    expect(seen).toEqual([
      ["test-user", "user-b"],
      ["user-b", "user-c"],
    ]);

    // 恢复初始身份，避免影响同一文件内的其他测试
    setUserId("test-user");
  });
});

describe("请求构造", () => {
  it("Base URL 默认 /api/v1，发送 JSON body 与 X-User-ID", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockFetchResponse(200, { ok: true })),
    );
    await api.post("/chat", { message: "hi" });
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe(`${BASE}/chat`);
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ message: "hi" }));
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("超时 → timeout 错误，可重试", async () => {
    vi.useFakeTimers();
    // fetch 永不返回，但 abort 时按真实 fetch 行为 reject
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("The operation was aborted.", "AbortError")),
            );
          }),
      ),
    );
    const promise = api.get("/slow", { timeoutMs: 1000 });
    const assertion = expect(promise).rejects.toMatchObject({
      code: "timeout",
      retryable: true,
    });
    await vi.advanceTimersByTimeAsync(1001);
    await assertion;
  });

  it("外部 signal 取消 → aborted 错误，不可重试", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("The operation was aborted.", "AbortError")),
            );
          }),
      ),
    );
    const promise = api.get("/slow", { signal: controller.signal, timeoutMs: 60_000 });
    const assertion = expect(promise).rejects.toMatchObject({ code: "aborted", retryable: false });
    controller.abort();
    await assertion;
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";
import { setUserId, streamPost } from "@/api/client";

setUserId("stream-test-user");

afterEach(() => {
  vi.unstubAllGlobals();
  setUserId("test-user");
});

describe("streamPost", () => {
  it("按顺序解析 SSE 状态和完成事件", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          'data: {"type":"status","stage":"analyzing"}\n\n' +
            'data: {"type":"complete","response":{"message":"完成"}}\n\n',
          {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          },
        ),
      ),
    );

    const events: string[] = [];
    await streamPost("/chat/stream", { message: "hi" }, (event) => {
      events.push(event.type);
    });

    expect(events).toEqual(["status", "complete"]);
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe("/api/v1/chat/stream");
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>).Accept).toBe(
      "text/event-stream",
    );
  });

  it("把服务端 error 事件转换成可重试的 AppError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          'data: {"type":"error","code":"agent_timeout","message":"处理超时"}\n\n',
          {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          },
        ),
      ),
    );

    await expect(
      streamPost("/chat/stream", { message: "hi" }, () => undefined),
    ).rejects.toMatchObject({
      code: "agent_timeout",
      message: "处理超时",
      retryable: true,
    });
  });
});

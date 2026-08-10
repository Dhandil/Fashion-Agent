/**
 * 前端 API 客户端。
 *
 * 统一处理身份请求头、超时、取消、错误格式和 SSE 流式响应。
 */

export type AppError = {
  status: number | null;
  code: string;
  message: string;
  requestId?: string;
  fieldErrors?: Record<string, string[]>;
  retryable: boolean;
};

export type StreamEvent = {
  type: "status" | "complete" | "error";
  stage?: string;
  conversation_id?: string;
  response?: unknown;
  code?: string;
  message?: string;
};

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const DEFAULT_TIMEOUT_MS = 120_000;

let userId: string | null = null;

type UserChangeHandler = (previous: string | null, next: string) => void;
let userChangeHandlers: UserChangeHandler[] = [];

function resolveRequestUrl(path: string): string {
  // 后端返回的私有图片地址已经包含 /api/v1，不能再次拼接 API 前缀。
  if (/^https?:\/\//.test(path) || path.startsWith(BASE_URL)) return path;
  return `${BASE_URL}${path}`;
}

export function setUserId(id: string): void {
  if (userId === id) return;
  const previous = userId;
  userId = id;
  for (const handler of userChangeHandlers) handler(previous, id);
}

export function onUserChange(handler: UserChangeHandler): () => void {
  userChangeHandlers.push(handler);
  return () => {
    userChangeHandlers = userChangeHandlers.filter((item) => item !== handler);
  };
}

export function getUserId(): string {
  if (!userId) throw new Error("User identity is not configured.");
  return userId;
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  rawBody?: BodyInit;
  xUserId?: string;
  timeoutMs?: number;
  signal?: AbortSignal;
  anonymous?: boolean;
};

function buildError(
  status: number | null,
  code: string,
  message: string,
  retryable: boolean,
  requestId?: string,
  fieldErrors?: Record<string, string[]>,
): AppError {
  return { status, code, message, requestId, fieldErrors, retryable };
}

function normalizeError(response: Response, body: unknown): AppError {
  const status = response.status;
  const requestId = response.headers.get("X-Request-ID") ?? undefined;
  const retryable = status >= 500 || status === 429;

  if (status === 422 && body && typeof body === "object" && "detail" in body) {
    const detail = (body as Record<string, unknown>).detail;
    const fieldErrors: Record<string, string[]> = {};
    if (Array.isArray(detail)) {
      for (const item of detail) {
        if (!item || typeof item !== "object") continue;
        const error = item as Record<string, unknown>;
        const location = Array.isArray(error.loc)
          ? error.loc.slice(1).join(".")
          : "body";
        (fieldErrors[location] ??= []).push(String(error.msg ?? "输入值无效。"));
      }
    }
    return buildError(422, "validation_error", "请检查输入内容。", false, requestId, fieldErrors);
  }

  if (body && typeof body === "object" && "code" in body && "message" in body) {
    const error = body as Record<string, unknown>;
    return buildError(
      status,
      String(error.code),
      String(error.message),
      retryable,
      requestId,
    );
  }

  return buildError(
    status,
    "unexpected_error",
    retryable ? "服务暂时不可用，请稍后重试。" : "请求失败。",
    retryable,
    requestId,
  );
}

export function isAppError(err: unknown): err is AppError {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    "message" in err &&
    "retryable" in err
  );
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, rawBody, xUserId, timeoutMs, signal, anonymous, ...init } = options;
  const effectiveUserId = anonymous ? null : (xUserId ?? userId);
  if (!effectiveUserId && !anonymous) {
    throw buildError(401, "unauthorized", "用户身份未配置。", false);
  }

  const headers: Record<string, string> = {};
  if (effectiveUserId) headers["X-User-ID"] = effectiveUserId;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort);
  const cleanup = () => {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  };

  let response: Response;
  try {
    response = await fetch(resolveRequestUrl(path), {
      ...init,
      method: init.method,
      headers: { ...headers, ...(init.headers as Record<string, string> | undefined) },
      body: rawBody ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal: controller.signal,
    });
  } catch (err) {
    cleanup();
    if (signal?.aborted) throw buildError(null, "aborted", "请求已取消。", false);
    if (controller.signal.aborted) {
      throw buildError(null, "timeout", "请求超时，请稍后重试。", true);
    }
    throw buildError(null, "network_error", "网络连接失败，请稍后重试。", true);
  }

  if (response.status === 204) {
    cleanup();
    return undefined as T;
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  cleanup();

  if (!response.ok) throw normalizeError(response, payload);
  return payload as T;
}

async function requestBlob(
  path: string,
  options: Omit<RequestOptions, "body" | "rawBody"> = {},
): Promise<Blob> {
  const { xUserId, timeoutMs, signal, anonymous, ...init } = options;
  const effectiveUserId = anonymous ? null : (xUserId ?? userId);
  if (!effectiveUserId && !anonymous) {
    throw buildError(401, "unauthorized", "用户身份未配置。", false);
  }

  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  };
  if (effectiveUserId) headers["X-User-ID"] = effectiveUserId;

  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort);

  try {
    const response = await fetch(resolveRequestUrl(path), {
      ...init,
      method: "GET",
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw normalizeError(response, payload);
    }

    return await response.blob();
  } catch (err) {
    if (err && typeof err === "object" && "code" in err) throw err;
    if (signal?.aborted) {
      throw buildError(null, "aborted", "请求已取消。", false);
    }
    if (controller.signal.aborted) {
      throw buildError(null, "timeout", "请求超时，请稍后重试。", true);
    }
    throw buildError(null, "network_error", "网络连接失败，请稍后重试。", true);
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  }
}

export const api = {
  get<T>(path: string, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "GET" });
  },
  post<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "POST", body });
  },
  patch<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "PATCH", body });
  },
  put<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "PUT", body });
  },
  putBinary<T>(path: string, body: BodyInit, contentType: string, options?: RequestOptions) {
    return request<T>(path, {
      ...options,
      method: "PUT",
      rawBody: body,
      headers: {
        ...(options?.headers as Record<string, string> | undefined),
        "Content-Type": contentType,
      },
    });
  },
  getBlob(path: string, options?: Omit<RequestOptions, "body" | "rawBody">) {
    return requestBlob(path, options);
  },
  delete<T>(path: string, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "DELETE" });
  },
};

/** 发送 JSON 请求并逐个消费 Server-Sent Events。 */
export async function streamPost(
  path: string,
  body: unknown,
  onEvent: (event: StreamEvent) => void,
  options: Omit<RequestOptions, "body" | "method"> = {},
): Promise<void> {
  const { xUserId, timeoutMs, signal, anonymous, headers: extraHeaders, ...init } = options;
  const effectiveUserId = anonymous ? null : (xUserId ?? userId);
  if (!effectiveUserId && !anonymous) {
    throw buildError(401, "unauthorized", "用户身份未配置。", false);
  }

  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string> | undefined),
  };
  if (effectiveUserId) headers["X-User-ID"] = effectiveUserId;

  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort);
  const cleanup = () => {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  };

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    cleanup();
    if (signal?.aborted) throw buildError(null, "aborted", "请求已取消。", false);
    if (controller.signal.aborted) {
      throw buildError(null, "timeout", "请求超时，请稍后重试。", true);
    }
    throw buildError(null, "network_error", "网络连接失败，请稍后重试。", true);
  }

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    cleanup();
    throw normalizeError(response, payload);
  }

  if (!response.body) {
    cleanup();
    throw buildError(null, "empty_stream", "服务器返回了空的对话流。", true);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const consumeBlock = (block: string) => {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    let event: StreamEvent;
    try {
      event = JSON.parse(data) as StreamEvent;
    } catch {
      throw buildError(null, "invalid_stream_event", "收到的流式数据格式无效。", true);
    }
    onEvent(event);
    if (event.type === "error") {
      throw buildError(
        null,
        event.code ?? "agent_error",
        event.message ?? "助手暂时无法完成这次请求。",
        true,
      );
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) consumeBlock(block);
      if (done) break;
    }
    if (buffer.trim()) consumeBlock(buffer);
  } catch (err) {
    if (isAppError(err)) throw err;
    if (signal?.aborted) throw buildError(null, "aborted", "请求已取消。", false);
    if (controller.signal.aborted) {
      throw buildError(null, "timeout", "对话流响应超时，请稍后重试。", true);
    }
    throw buildError(null, "stream_error", "对话流被中断，请稍后重试。", true);
  } finally {
    cleanup();
    reader.releaseLock();
  }
}

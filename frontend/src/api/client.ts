/**
 * API Client · 来自 frontend §8
 *
 * - Base URL: /api/v1
 * - 开发和测试环境通过 X-User-ID 传递身份
 * - 错误归一化为 AppError
 * - 只有幂等 GET 支持有限自动重试
 */

// ── 类型 ──

/** 归一化错误 · frontend §8.4 */
export type AppError = {
  status: number | null;
  code: string;
  message: string;
  requestId?: string;
  fieldErrors?: Record<string, string[]>;
  retryable: boolean;
};

// ── 配置 ──

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** 默认请求超时：模型/识别类请求可单独覆盖 */
const DEFAULT_TIMEOUT_MS = 120_000;

let userId: string | null = null;

/** 用户身份变化回调（用于清空按用户隔离的缓存） */
type UserChangeHandler = (previous: string | null, next: string) => void;
let userChangeHandlers: UserChangeHandler[] = [];

export function setUserId(id: string): void {
  if (userId === id) return;
  const previous = userId;
  userId = id;
  for (const handler of userChangeHandlers) {
    handler(previous, id);
  }
}

/** 注册用户切换回调，返回取消注册函数 */
export function onUserChange(handler: UserChangeHandler): () => void {
  userChangeHandlers.push(handler);
  return () => {
    userChangeHandlers = userChangeHandlers.filter((h) => h !== handler);
  };
}

export function getUserId(): string {
  if (!userId) throw new Error("用户身份未设置");
  return userId;
}

// ── 请求构造 ──

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** 开发环境临时身份，生产必须替换 */
  xUserId?: string;
  /** 超时毫秒数，默认 120s */
  timeoutMs?: number;
  /** 外部取消信号（如用户主动取消） */
  signal?: AbortSignal;
  /** 匿名请求：不要求也不携带 X-User-ID（如健康检查等公开端点） */
  anonymous?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, xUserId, timeoutMs, signal, anonymous, ...init } = options;

  const effectiveUserId = anonymous ? null : (xUserId ?? userId);
  if (!effectiveUserId && !anonymous) {
    throw buildError(401, "unauthorized", "用户身份未设置，请先配置 X-User-ID。", false);
  }

  const headers: Record<string, string> = {};
  if (effectiveUserId) {
    headers["X-User-ID"] = effectiveUserId;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  // 超时控制 + 外部取消合并
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { ...headers, ...(init.headers as Record<string, string> | undefined) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (signal?.aborted) {
      throw buildError(null, "aborted", "请求已取消。", false);
    }
    if (controller.signal.aborted) {
      throw buildError(null, "timeout", "请求超时，请稍后重试。", true);
    }
    throw buildError(null, "network_error", "网络连接失败，请检查网络后重试。", true);
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw normalizeError(response, payload);
  }

  return payload as T;
}

// ── 错误归一化 · frontend §8.4 ──

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
  const isServerError = status >= 500;
  // 优先从响应头读取 Request ID，其次从错误响应体读取
  const headerRequestId = response.headers.get("X-Request-ID") ?? undefined;
  const requestId =
    headerRequestId ??
    (body && typeof body === "object" && "request_id" in body
      ? String((body as Record<string, unknown>).request_id)
      : undefined);

  // FastAPI/Pydantic 422
  if (status === 422 && body && typeof body === "object" && "detail" in body) {
    const detail = (body as Record<string, unknown>).detail;
    const fieldErrors: Record<string, string[]> = {};
    if (Array.isArray(detail)) {
      for (const err of detail) {
        const loc = Array.isArray(err.loc) ? err.loc.slice(1).join(".") : "body";
        (fieldErrors[loc] ??= []).push(String(err.msg ?? "无效值"));
      }
    }
    return buildError(422, "validation_error", "请检查输入内容。", false, requestId, fieldErrors);
  }

  // 项目 ErrorResponse
  if (body && typeof body === "object" && "code" in body && "message" in body) {
    const b = body as Record<string, unknown>;
    return buildError(
      status,
      String(b.code),
      String(b.message),
      isServerError || status === 429,
      requestId,
    );
  }

  // 兜底
  return buildError(
    status,
    "unexpected_error",
    isServerError ? "服务暂时不可用，请稍后重试。" : "请求失败，请稍后重试。",
    isServerError,
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

// ── HTTP 方法快捷函数 ──

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
  delete<T>(path: string, options?: RequestOptions) {
    return request<T>(path, { ...options, method: "DELETE" });
  },
};

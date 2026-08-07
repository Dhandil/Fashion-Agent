import { describe, expect, it, beforeEach } from "vitest";
import {
  conversationStorageKey,
  restoreConversationId,
  clearStoredConversationId,
} from "@/features/conversation/api";
import { setUserId } from "@/api/client";

describe("会话 ID 存储 · 按用户隔离", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("key 包含用户 ID，不同用户不共用会话", () => {
    expect(conversationStorageKey("user-a")).toBe("fashion-agent-cid:user-a");
    expect(conversationStorageKey("user-b")).toBe("fashion-agent-cid:user-b");
    expect(conversationStorageKey("user-a")).not.toBe(conversationStorageKey("user-b"));
  });

  it("restore/clear 只影响当前用户的 key", () => {
    // 用户 A 存会话
    sessionStorage.setItem(conversationStorageKey("user-a"), "cid-a");
    sessionStorage.setItem(conversationStorageKey("user-b"), "cid-b");

    setUserId("user-a");
    expect(restoreConversationId()).toBe("cid-a");

    // 切换用户 B 后读到的是 B 的会话
    setUserId("user-b");
    expect(restoreConversationId()).toBe("cid-b");

    // B 清除会话不影响 A
    clearStoredConversationId();
    expect(sessionStorage.getItem(conversationStorageKey("user-b"))).toBeNull();
    expect(sessionStorage.getItem(conversationStorageKey("user-a"))).toBe("cid-a");
  });
});

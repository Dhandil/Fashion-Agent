/**
 * 对话状态管理 · frontend §6.1 + §8.3
 *
 * - 同一会话只允许一个请求在途
 * - conversation_id 首次成功后保存
 * - 消息保存在内存中（当前无历史消息 API）
 */

import { create } from "zustand";
import type { components } from "@/api/generated/schema";

// ── 本地类型 ──

export type ChatMessage = {
  id: string;
  role: "user" | "agent";
  text: string;
  /** 只有 agent 消息才可能携带结构化数据 */
  outfit?: components["schemas"]["OutfitRecommendation"] | null;
  outfitGap?: components["schemas"]["OutfitGapReport"] | null;
  outfitIssues?: components["schemas"]["OutfitFeasibilityIssue"][] | null;
  sources?: string[];
  createdAt: number;
};

type SubmitStatus = "idle" | "submitting" | "success" | "error";

type ChatState = {
  /** 当前会话 ID，首次成功后由服务端返回 */
  conversationId: string | null;
  /** 本轮消息列表 */
  messages: ChatMessage[];
  /** 提交状态 */
  status: SubmitStatus;
  /** 最近一次错误 */
  error: string | null;

  // 操作
  setConversationId: (id: string) => void;
  addUserMessage: (text: string) => void;
  addAgentMessage: (msg: Omit<ChatMessage, "id" | "role" | "createdAt">) => void;
  setStatus: (status: SubmitStatus, error?: string | null) => void;
  endSession: () => void;
};

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  messages: [],
  status: "idle",
  error: null,

  setConversationId: (id) => set({ conversationId: id }),

  addUserMessage: (text) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: "user",
          text,
          createdAt: Date.now(),
        },
      ],
    })),

  addAgentMessage: (msg) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...msg,
          id: crypto.randomUUID(),
          role: "agent",
          createdAt: Date.now(),
        },
      ],
    })),

  setStatus: (status, error = null) => set({ status, error }),

  endSession: () =>
    set({
      conversationId: null,
      messages: [],
      status: "idle",
      error: null,
    }),
}));

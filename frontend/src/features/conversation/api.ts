/**
 * 对话 API hooks
 */

import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  api,
  getUserId,
  isAppError,
  streamPost,
  type AppError,
} from "@/api/client";
import type { components } from "@/api/generated/schema";
import { useChatStore, type WeatherSnapshot } from "@/stores/chat";
import type { WeatherQuery } from "@/features/conversation/PromptComposer";

type ChatRequest = components["schemas"]["ChatRequest"];
type ChatResponse = components["schemas"]["ChatResponse"];
type ChatResponseWithWeather = ChatResponse & {
  weather?: WeatherSnapshot | null;
};
type WeatherInput = components["schemas"]["WeatherContextInput"];

/** sessionStorage key 按用户隔离，避免不同用户串会话 */
export function conversationStorageKey(userId: string): string {
  return `fashion-agent-cid:${userId}`;
}

export function useSendMessage() {
  const {
    conversationId,
    setConversationId,
    addUserMessage,
    addAgentMessage,
    setStatus,
    setThinkingStage,
    status,
  } = useChatStore();
  const [error, setError] = useState<AppError | null>(null);

  const send = useCallback(
    async (
      message: string,
      weather?: WeatherInput,
      weatherQuery?: WeatherQuery,
    ) => {
      if (status === "submitting" || !message.trim()) return;

      setStatus("submitting");
      setError(null);
      addUserMessage(message.trim());

      try {
        const requestMessage = weatherQuery
          ? message.trim()
          : message.trim();
        const body: ChatRequest = {
          message: requestMessage,
          conversation_id: conversationId,
          weather: weather ?? null,
          weather_query: weatherQuery ?? null,
        };

        const streamResult: { value: ChatResponseWithWeather | null } = {
          value: null,
        };
        await streamPost("/chat/stream", body, (event) => {
          if (event.type === "status") {
            setThinkingStage(event.stage ?? "working");
          } else if (event.type === "complete") {
            streamResult.value = event.response as ChatResponseWithWeather;
          }
        });
        if (!streamResult.value) {
          throw new Error("流式响应缺少完整结果");
        }
        const res = streamResult.value;

        // 首次成功后保存会话 ID（按用户隔离）
        if (!conversationId && res.conversation_id) {
          setConversationId(res.conversation_id);
          try {
            sessionStorage.setItem(
              conversationStorageKey(getUserId()),
              res.conversation_id,
            );
          } catch {
            // Session Storage 不可用时忽略
          }
        }

        addAgentMessage({
          text: res.message,
          outfit: res.outfit ?? null,
          outfitGap: res.outfit_gap ?? null,
          outfitIssues: res.outfit_issues ?? null,
          sources: res.sources ?? undefined,
          weather: res.weather ?? null,
        });

        setStatus("success");
      } catch (err) {
        const appErr = isAppError(err) ? err : null;
        setError(
          appErr ?? {
            status: null,
            code: "unknown",
            message: "发送失败，请稍后重试。",
            retryable: true,
          },
        );
        setStatus("error", appErr?.message ?? "发送失败");
      }
    },
    [
      conversationId,
      setConversationId,
      addUserMessage,
      addAgentMessage,
      setStatus,
      setThinkingStage,
      status,
    ],
  );

  return { send, error, status };
}

export function useSaveOutfit() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const qc = useQueryClient();

  const save = useCallback(
    async (conversationId: string) => {
      setSaving(true);
      setError(null);
      try {
        await api.post("/outfits", {
          conversation_id: conversationId,
        } as components["schemas"]["OutfitConfirmRequest"]);
        // 保存成功后刷新穿搭列表缓存
        qc.invalidateQueries({ queryKey: ["outfits"] });
        return true;
      } catch (err) {
        setError(
          isAppError(err)
            ? err
            : { status: null, code: "unknown", message: "保存失败", retryable: true },
        );
        return false;
      } finally {
        setSaving(false);
      }
    },
    [qc],
  );

  return { save, saving, error };
}

/** 恢复当前用户的会话 ID */
export function restoreConversationId(): string | null {
  try {
    return sessionStorage.getItem(conversationStorageKey(getUserId()));
  } catch {
    return null;
  }
}

/** 删除当前用户的会话 ID 记录 */
export function clearStoredConversationId(): void {
  try {
    sessionStorage.removeItem(conversationStorageKey(getUserId()));
  } catch {
    // 忽略
  }
}

/** 删除后端会话状态（聊天记忆、Checkpoint 等） */
export async function deleteConversation(conversationId: string): Promise<void> {
  await api.delete(`/chat/${encodeURIComponent(conversationId)}`);
}

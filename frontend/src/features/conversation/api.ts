/** 对话接口 Hooks：负责发送、重试和保存穿搭。 */

import { useCallback, useRef, useState } from "react";
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

/** 每个用户使用独立的会话缓存键，避免切换用户后串用会话。 */
export function conversationStorageKey(userId: string): string {
  return `fashion-agent-cid:${userId}`;
}

type PendingRequest = {
  message: string;
  weather?: WeatherInput;
  weatherQuery?: WeatherQuery;
  conversationId: string | null;
};

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
  const [retryRequest, setRetryRequest] = useState<PendingRequest | null>(null);
  // 用 ref 做同步互斥锁，避免用户连续点击时 React 状态尚未刷新而重复发送。
  const sendingRef = useRef(false);

  const execute = useCallback(
    async (request: PendingRequest, appendUserMessage: boolean) => {
      if (sendingRef.current) return;
      sendingRef.current = true;
      setStatus("submitting");
      setError(null);
      if (appendUserMessage) addUserMessage(request.message);
      // 后端会在第一条 status 事件中返回会话 ID；失败重试时复用它，
      // 避免同一条用户消息因为网络中断而创建多个会话。
      let activeConversationId = request.conversationId;

      try {
        const body: ChatRequest = {
          message: request.message,
          conversation_id: activeConversationId,
          weather: request.weather ?? null,
          weather_query: request.weatherQuery ?? null,
        };
        const streamResult: { value: ChatResponseWithWeather | null } = {
          value: null,
        };
        await streamPost("/chat/stream", body, (event) => {
          if (event.type === "status") {
            activeConversationId = event.conversation_id ?? activeConversationId;
            setThinkingStage(event.stage ?? "working");
          } else if (event.type === "complete") {
            streamResult.value = event.response as ChatResponseWithWeather;
          }
        });

        if (!streamResult.value) {
          throw new Error("Stream response did not contain a complete result.");
        }
        const response = streamResult.value;

        // 成功后保存会话 ID；重试场景也要把后端已分配的 ID 写回前端。
        if (response.conversation_id) {
          setConversationId(response.conversation_id);
          try {
            sessionStorage.setItem(
              conversationStorageKey(getUserId()),
              response.conversation_id,
            );
          } catch {
            // 浏览器禁用 Session Storage 时不影响对话本身。
          }
        }

        addAgentMessage({
          text: response.message,
          outfit: response.outfit ?? null,
          outfitGap: response.outfit_gap ?? null,
          outfitIssues: response.outfit_issues ?? null,
          sources: response.sources ?? undefined,
          weather: response.weather ?? null,
        });
        setRetryRequest(null);
        setStatus("success");
      } catch (err) {
        const appError = isAppError(err)
          ? err
          : {
              status: null,
              code: "unknown",
              message: "发送失败，请稍后重试。",
              retryable: true,
            } satisfies AppError;
        setError(appError);
        setRetryRequest({ ...request, conversationId: activeConversationId });
        setStatus("error", appError.message);
      } finally {
        sendingRef.current = false;
      }
    },
    [
      addAgentMessage,
      addUserMessage,
      setConversationId,
      setStatus,
      setThinkingStage,
    ],
  );

  const send = useCallback(
    (message: string, weather?: WeatherInput, weatherQuery?: WeatherQuery) => {
      const trimmedMessage = message.trim();
      if (!trimmedMessage || sendingRef.current) return;
      void execute(
        {
          message: trimmedMessage,
          weather,
          weatherQuery,
          conversationId,
        },
        true,
      );
    },
    [conversationId, execute],
  );

  const retry = useCallback(() => {
    if (!retryRequest || sendingRef.current) return;
    void execute(retryRequest, false);
  }, [execute, retryRequest]);

  return { send, retry, error, status };
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
        qc.invalidateQueries({ queryKey: ["outfits"] });
        return true;
      } catch (err) {
        setError(
          isAppError(err)
            ? err
            : {
                status: null,
                code: "unknown",
                message: "保存穿搭失败。",
                retryable: true,
              },
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

/** 恢复当前用户最近一次会话 ID。 */
export function restoreConversationId(): string | null {
  try {
    return sessionStorage.getItem(conversationStorageKey(getUserId()));
  } catch {
    return null;
  }
}

/** 清理当前用户本地保存的会话 ID。 */
export function clearStoredConversationId(): void {
  try {
    sessionStorage.removeItem(conversationStorageKey(getUserId()));
  } catch {
    // 忽略不可用的存储环境。
  }
}

/** 删除后端会话及其短期记忆。 */
export async function deleteConversation(conversationId: string): Promise<void> {
  await api.delete(`/chat/${encodeURIComponent(conversationId)}`);
}

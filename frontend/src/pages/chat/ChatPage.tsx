import { useEffect, useState, useCallback } from "react";
import { useChatStore } from "@/stores/chat";
import {
  restoreConversationId,
  clearStoredConversationId,
  deleteConversation,
  useSendMessage,
} from "@/features/conversation/api";
import WelcomeState from "@/features/conversation/WelcomeState";
import ConversationView from "@/features/conversation/ConversationView";
import { X, Loader2 } from "lucide-react";
import { isAppError, type AppError } from "@/api/client";

export default function ChatPage() {
  const { messages, endSession, conversationId } = useChatStore();
  const { send } = useSendMessage();
  const [ending, setEnding] = useState(false);
  const [endError, setEndError] = useState<string | null>(null);

  // 恢复会话 ID
  useEffect(() => {
    const saved = restoreConversationId();
    if (saved) {
      useChatStore.getState().setConversationId(saved);
    }
  }, []);

  const hasMessages = messages.length > 0;

  /** 结束会话：删除后端记忆 → 清理本地状态与 sessionStorage */
  const handleEndSession = useCallback(async () => {
    if (ending) return;
    setEnding(true);
    setEndError(null);
    try {
      if (conversationId) {
        await deleteConversation(conversationId);
      }
    } catch (err) {
      // 后端删除失败时仍清理本地，避免旧会话残留；提示用户后端记忆可能未删干净
      setEndError(
        isAppError(err)
          ? (err as AppError).message
          : "后端会话清理失败，本地会话已结束。",
      );
    } finally {
      clearStoredConversationId();
      endSession();
      setEnding(false);
    }
  }, [conversationId, ending, endSession]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 顶栏：会话操作 */}
      {hasMessages && (
        <div className="flex items-center justify-between px-16 md:px-32 py-12 border-b border-border bg-surface">
          <span className="text-small text-text-secondary">智能搭配</span>
          <div className="flex items-center gap-8">
            <button
              onClick={handleEndSession}
              disabled={ending}
              className="inline-flex items-center gap-6 text-small text-text-secondary
                         hover:text-danger disabled:opacity-50 transition-colors"
            >
              {ending ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />}
              {ending ? "结束中…" : "结束会话"}
            </button>
          </div>
        </div>
      )}

      {endError && (
        <div className="mx-16 md:mx-32 mt-12 rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12" role="alert">
          <p className="text-small text-danger">{endError}</p>
        </div>
      )}

      {/* 页面主体 */}
      {hasMessages ? (
        <ConversationView />
      ) : (
        <WelcomeState onSend={send} />
      )}
    </div>
  );
}

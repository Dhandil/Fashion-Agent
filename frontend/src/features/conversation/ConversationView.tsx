import { Loader2 } from "lucide-react";
import { useChatStore } from "@/stores/chat";
import { useSaveOutfit, useSendMessage } from "@/features/conversation/api";
import MessageList from "@/features/conversation/MessageList";
import PromptComposer from "@/features/conversation/PromptComposer";

export default function ConversationView() {
  const { messages, status, thinkingStage, conversationId } = useChatStore();
  const { send, retry, error: sendError } = useSendMessage();
  const { save, saving, error: saveError } = useSaveOutfit();

  const handleSaveOutfit = () => {
    if (!conversationId) return;
    void save(conversationId);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {status === "submitting" && (
        <div className="flex shrink-0 items-center gap-8 border-b border-border bg-surface-subtle px-16 py-8 md:px-32">
          <Loader2 size={16} className="text-brand animate-spin" />
          <span className="text-small text-text-secondary">
            {thinkingStage === "working"
              ? "正在整理穿搭方案…"
              : "正在分析衣橱、天气和知识…"}
          </span>
        </div>
      )}

      {sendError && (
        <div
          className="mx-16 md:mx-32 mt-12 flex items-center justify-between gap-12 rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12"
          role="alert"
        >
          <p className="text-small text-danger">{sendError.message}</p>
          {sendError.retryable && status !== "submitting" && (
            <button
              type="button"
              className="shrink-0 rounded-button border border-danger/40 px-12 py-6 text-small text-danger hover:bg-danger/[0.08]"
              onClick={retry}
            >
              重试
            </button>
          )}
        </div>
      )}

      {saveError && (
        <div
          className="mx-16 md:mx-32 mt-12 rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12"
          role="alert"
        >
          <p className="text-small text-danger">保存穿搭失败：{saveError.message}</p>
        </div>
      )}

      <MessageList
        messages={messages}
        onSaveOutfit={handleSaveOutfit}
        savingOutfit={saving}
      />

      <PromptComposer onSubmit={send} disabled={status === "submitting"} />
    </div>
  );
}

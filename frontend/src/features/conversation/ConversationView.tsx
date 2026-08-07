import { useChatStore } from "@/stores/chat";
import { useSendMessage, useSaveOutfit } from "@/features/conversation/api";
import MessageList from "@/features/conversation/MessageList";
import PromptComposer from "@/features/conversation/PromptComposer";
import { Loader2 } from "lucide-react";

export default function ConversationView() {
  const { messages, status, conversationId } = useChatStore();
  const { send } = useSendMessage();
  const { save, saving } = useSaveOutfit();

  const handleSaveOutfit = () => {
    if (!conversationId) return;
    save(conversationId);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 提交中状态 */}
      {status === "submitting" && (
        <div className="flex items-center gap-8 px-16 md:px-32 py-8 bg-surface-subtle border-b border-border">
          <Loader2 size={16} className="text-brand animate-spin" />
          <span className="text-small text-text-secondary">正在分析衣橱、天气和知识…</span>
        </div>
      )}

      {/* 消息列表 */}
      <MessageList
        messages={messages}
        onSaveOutfit={handleSaveOutfit}
        savingOutfit={saving}
      />

      {/* 输入区 */}
      <PromptComposer
        onSubmit={send}
        disabled={status === "submitting"}
      />
    </div>
  );
}

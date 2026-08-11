import type { ChatMessage } from "@/stores/chat";
import UserMessage from "./UserMessage";
import AgentMessage from "./AgentMessage";

type Props = {
  messages: ChatMessage[];
  onSaveOutfit: () => void;
  savingOutfit: boolean;
};

export default function MessageList({ messages, onSaveOutfit, savingOutfit }: Props) {
  if (messages.length === 0) return null;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-16 md:px-32">
      <div className="max-w-chat mx-auto space-y-24 py-24">
        {messages.map((msg) =>
          msg.role === "user" ? (
            <UserMessage key={msg.id} message={msg} />
          ) : (
            <AgentMessage
              key={msg.id}
              message={msg}
              onSaveOutfit={onSaveOutfit}
              savingOutfit={savingOutfit}
            />
          ),
        )}

        {/* 移动端底部留白：避免被 PromptComposer + MobileNav 遮挡 */}
        <div className="h-64 md:hidden" />
      </div>
    </div>
  );
}

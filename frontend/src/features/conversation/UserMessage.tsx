import type { ChatMessage } from "@/stores/chat";

type Props = { message: ChatMessage };

export default function UserMessage({ message }: Props) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-card rounded-br-input bg-surface-subtle px-16 py-12">
        <p className="text-body text-text-primary whitespace-pre-wrap break-words">
          {message.text}
        </p>
      </div>
    </div>
  );
}

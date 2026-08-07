import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

type Props = {
  onSubmit: (message: string) => void;
  disabled?: boolean;
};

export default function PromptComposer({ onSubmit, disabled = false }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整高度
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="sticky bottom-0 bg-canvas pt-12 pb-24 md:pb-32">
      <div className="flex items-end gap-12 rounded-card border border-border bg-surface p-12 shadow-sm">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的穿搭需求…"
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-body text-text-primary placeholder:text-text-secondary
                     outline-none py-4 px-4 max-h-[160px]"
          aria-label="穿搭需求输入"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex items-center justify-center w-40 h-40 rounded-input bg-brand text-surface
                     hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors shrink-0 touch-target"
          aria-label="发送"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="text-caption text-text-secondary mt-8 px-4">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  );
}

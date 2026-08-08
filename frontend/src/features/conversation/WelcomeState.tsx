import { Sparkles } from "lucide-react";
import PromptComposer from "@/features/conversation/PromptComposer";

type Props = {
  onSend: (message: string) => void;
};

const QUICK_PROMPTS = ["明天通勤怎么穿", "周末约会搭一套", "从衣橱帮我搭配"];

export default function WelcomeState({ onSend }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-16 py-48">
      <div className="max-w-chat w-full text-center space-y-32">
        {/* 主标题 */}
        <div className="space-y-12">
          <div className="inline-flex items-center justify-center w-56 h-56 rounded-card-lg bg-brand/10 mb-8">
            <Sparkles size={28} className="text-brand" />
          </div>
          <h2 className="text-display text-text-primary">今天想为哪个场景搭配？</h2>
          <p className="text-body text-text-secondary max-w-md mx-auto">
            告诉我场景、天气或你想穿的某件衣服，Agent 会优先从你的衣橱中生成可执行的穿搭方案。
          </p>
        </div>

        {/* 快捷提示 */}
        <div className="flex flex-wrap justify-center gap-8">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onSend(prompt)}
              className="rounded-tag border border-border px-16 py-8 text-small text-text-secondary
                         hover:bg-surface-subtle hover:text-text-primary transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>

        <PromptComposer onSubmit={onSend} />
      </div>
    </div>
  );
}

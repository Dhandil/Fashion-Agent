import { useEffect, useState } from "react";
import { X, ThumbsUp, ThumbsDown } from "lucide-react";
import type { components } from "@/api/generated/schema";

type Sentiment = components["schemas"]["OutfitFeedbackSentiment"];

type Props = {
  open: boolean;
  initialSentiment: Sentiment | null;
  initialComment: string;
  onClose: () => void;
  onSubmit: (sentiment: Sentiment | null, comment: string) => Promise<void>;
};

/** Outfit 反馈对话框 · ui-design §8.3 */
export default function FeedbackDialog({
  open,
  initialSentiment,
  initialComment,
  onClose,
  onSubmit,
}: Props) {
  const [sentiment, setSentiment] = useState<Sentiment | null>(initialSentiment);
  const [comment, setComment] = useState(initialComment);
  const [submitting, setSubmitting] = useState(false);

  // 每次打开或服务端反馈刷新时，都以最新已保存反馈初始化草稿。
  useEffect(() => {
    if (open) {
      setSentiment(initialSentiment);
      setComment(initialComment);
      setSubmitting(false);
    }
  }, [open, initialSentiment, initialComment]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!sentiment && !comment.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(sentiment, comment.trim());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-text-primary/40 p-16"
      role="dialog"
      aria-modal="true"
      aria-label="Outfit 反馈"
    >
      <div className="w-full max-w-md rounded-card-lg bg-surface p-24 space-y-20 shadow-lg">
        <div className="flex items-center justify-between">
          <h3 className="text-h3 text-text-primary">这套穿搭怎么样？</h3>
          <button type="button" onClick={onClose} className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle" aria-label="关闭">
            <X size={18} />
          </button>
        </div>

        {/* 态度选择 */}
        <div className="flex gap-16">
          <button
            type="button"
            onClick={() => setSentiment("like")}
            aria-pressed={sentiment === "like"}
            className={`flex-1 inline-flex items-center justify-center gap-8 px-16 py-12 rounded-card border transition-colors
              ${sentiment === "like" ? "border-success/50 bg-success/10 text-success" : "border-border text-text-secondary hover:bg-surface-subtle"}`}
          >
            <ThumbsUp size={20} />
            喜欢
          </button>
          <button
            type="button"
            onClick={() => setSentiment("dislike")}
            aria-pressed={sentiment === "dislike"}
            className={`flex-1 inline-flex items-center justify-center gap-8 px-16 py-12 rounded-card border transition-colors
              ${sentiment === "dislike" ? "border-danger/50 bg-danger/10 text-danger" : "border-border text-text-secondary hover:bg-surface-subtle"}`}
          >
            <ThumbsDown size={20} />
            不喜欢
          </button>
        </div>

        {/* 可选文字说明 */}
        <div className="space-y-4">
          <label htmlFor="feedback-comment" className="text-small text-text-secondary">
            补充说明（可选）
          </label>
          <textarea
            id="feedback-comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            placeholder="例如：不太适合通勤，希望更正式一些"
            className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand resize-none"
          />
        </div>

        {/* 说明 */}
        <p className="text-caption text-text-secondary">
          反馈会帮助产生待确认的偏好候选，不会自动修改你的长期档案。
        </p>

        {/* 操作 */}
        <div className="flex justify-end gap-12 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-16 py-8 rounded-input border border-border text-text-secondary hover:bg-surface-subtle transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={(!sentiment && !comment.trim()) || submitting}
            className="px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover disabled:opacity-50 transition-colors"
          >
            {submitting ? "提交中…" : "提交反馈"}
          </button>
        </div>
      </div>
    </div>
  );
}

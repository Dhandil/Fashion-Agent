import { useState } from "react";
import { X, Heart, MessageSquareText } from "lucide-react";
import type { components } from "@/api/generated/schema";
import SourceTag from "@/features/outfit/SourceTag";
import FeedbackDialog from "@/features/outfit/FeedbackDialog";
import { useSetOutfitFavorite, useOutfitFeedback } from "@/features/outfit/api";
import { useUpsertOutfitFeedback, useDeleteOutfitFeedback } from "@/features/outfit/api";
import { isAppError, type AppError } from "@/api/client";

type OutfitResponse = components["schemas"]["OutfitResponse"];

type Props = {
  outfit: OutfitResponse;
  onClose: () => void;
};

/** Outfit 详情抽屉 · ui-design §8.2 双栏 */
export default function OutfitDetailDrawer({ outfit, onClose }: Props) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const favoriteMutation = useSetOutfitFavorite();
  const feedbackMutation = useUpsertOutfitFeedback();
  const deleteFeedbackMutation = useDeleteOutfitFeedback();
  const { data: feedback } = useOutfitFeedback(outfit.outfit_id);

  const handleToggleFavorite = async () => {
    setPageError(null);
    try {
      await favoriteMutation.mutateAsync({
        id: outfit.outfit_id,
        isFavorite: !outfit.is_favorite,
      });
    } catch (err) {
      setPageError(isAppError(err) ? (err as AppError).message : "操作失败");
    }
  };

  const handleSubmitFeedback = async (
    sentiment: components["schemas"]["OutfitFeedbackSentiment"] | null,
    comment: string,
  ) => {
    setPageError(null);
    try {
      await feedbackMutation.mutateAsync({
        id: outfit.outfit_id,
        body: { sentiment, comment: comment || null },
      });
      setFeedbackOpen(false);
    } catch (err) {
      setPageError(isAppError(err) ? (err as AppError).message : "提交失败");
    }
  };

  const handleDeleteFeedback = async () => {
    setPageError(null);
    try {
      await deleteFeedbackMutation.mutateAsync(outfit.outfit_id);
    } catch (err) {
      setPageError(isAppError(err) ? (err as AppError).message : "删除失败");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-text-primary/40">
      <div className="w-full max-w-3xl h-full bg-canvas overflow-y-auto" role="dialog" aria-modal="true" aria-label={outfit.name}>
        {/* 头部 */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-24 py-16 bg-surface border-b border-border">
          <h2 className="text-h2 text-text-primary">{outfit.name}</h2>
          <button type="button" onClick={onClose} className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle" aria-label="关闭">
            <X size={20} />
          </button>
        </div>

        <div className="p-24 space-y-24">
          {pageError && (
            <div className="rounded-card border border-danger/30 bg-danger/[0.06] px-16 py-12" role="alert">
              <p className="text-small text-danger">{pageError}</p>
            </div>
          )}

          {/* 元信息 */}
          <div className="flex flex-wrap items-center gap-8">
            {outfit.scenario && (
              <span className="rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary">{outfit.scenario}</span>
            )}
            {outfit.season && (
              <span className="rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary">{outfit.season}</span>
            )}
            {outfit.style_tags.map((tag) => (
              <span key={tag} className="rounded-tag bg-surface-subtle px-10 py-2 text-small text-text-secondary">{tag}</span>
            ))}
          </div>

          {/* 双栏：单品组合 + 理由/操作 */}
          <div className="grid md:grid-cols-2 gap-24">
            {/* 左：单品组合 */}
            <div className="rounded-card border border-border bg-surface p-20 space-y-12">
              <h3 className="text-h3 text-text-primary">单品组合</h3>
              <ul className="space-y-10" role="list">
                {outfit.items.map((item, i) => (
                  <li key={i} className="flex items-start gap-10">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-8 flex-wrap">
                        <span className="text-body font-medium text-text-primary">{item.name}</span>
                        <SourceTag source={item.source} />
                      </div>
                      <p className="text-caption text-text-secondary mt-2">{item.role}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* 右：理由与操作 */}
            <div className="space-y-16">
              <div className="rounded-card border border-border bg-surface p-20">
                <h3 className="text-h3 text-text-primary mb-8">推荐理由</h3>
                <p className="text-body text-text-primary leading-relaxed">{outfit.recommendation_reason}</p>
                {outfit.notes && (
                  <div className="mt-12 rounded-card bg-warning/10 border border-warning/20 px-12 py-8">
                    <p className="text-small text-warning">{outfit.notes}</p>
                  </div>
                )}
              </div>

              {/* 操作 */}
              <div className="flex gap-8">
                <button
                  type="button"
                  onClick={handleToggleFavorite}
                  disabled={favoriteMutation.isPending}
                  className={`inline-flex items-center gap-8 px-14 py-8 rounded-input border transition-colors text-small disabled:opacity-50
                    ${outfit.is_favorite
                      ? "border-danger/40 bg-danger/10 text-danger"
                      : "border-border text-text-secondary hover:bg-surface-subtle"}`}
                >
                  <Heart size={16} className={outfit.is_favorite ? "fill-danger" : ""} />
                  {outfit.is_favorite ? "已收藏" : "收藏"}
                </button>
                <button
                  type="button"
                  onClick={() => setFeedbackOpen(true)}
                  className="inline-flex items-center gap-8 px-14 py-8 rounded-input border border-border
                             text-text-secondary hover:bg-surface-subtle transition-colors text-small"
                >
                  <MessageSquareText size={16} />
                  提供反馈
                </button>
              </div>

              {/* 已有反馈 */}
              {feedback && (feedback.sentiment || feedback.comment) && (
                <div className="rounded-card bg-surface-subtle p-16 space-y-8">
                  <p className="text-small text-text-secondary">我的反馈</p>
                  {feedback.sentiment && (
                    <p className="text-body text-text-primary">
                      {feedback.sentiment === "like" ? "👍 喜欢" : "👎 不喜欢"}
                    </p>
                  )}
                  {feedback.comment && (
                    <p className="text-small text-text-primary">{feedback.comment}</p>
                  )}
                  <button
                    type="button"
                    onClick={handleDeleteFeedback}
                    disabled={deleteFeedbackMutation.isPending}
                    className="text-caption text-text-secondary hover:text-danger underline"
                  >
                    删除反馈
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 反馈对话框 */}
      <FeedbackDialog
        open={feedbackOpen}
        initialSentiment={feedback?.sentiment ?? null}
        initialComment={feedback?.comment ?? ""}
        onClose={() => setFeedbackOpen(false)}
        onSubmit={handleSubmitFeedback}
      />
    </div>
  );
}

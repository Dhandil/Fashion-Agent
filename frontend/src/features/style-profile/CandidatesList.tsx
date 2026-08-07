import { useState } from "react";
import { Sparkles, Check } from "lucide-react";
import {
  usePreferenceCandidates,
  useConfirmCandidate,
} from "@/features/style-profile/api";
import { isAppError, type AppError } from "@/api/client";

const DIRECTION_LABEL: Record<string, string> = {
  prefer: "你可能更喜欢",
  avoid: "你可能想避免",
};

/** 待确认偏好候选 · ui-design §9.3 */
export default function CandidatesList() {
  const { data, isLoading } = usePreferenceCandidates();
  const confirmMutation = useConfirmCandidate();
  const [error, setError] = useState<string | null>(null);

  const candidates = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="rounded-card border border-border bg-surface p-24 animate-pulse space-y-12">
        <div className="h-20 bg-surface-subtle rounded w-1/3" />
        <div className="h-16 bg-surface-subtle rounded w-full" />
      </div>
    );
  }

  if (candidates.length === 0) {
    return null;
  }

  const handleConfirm = async (candidate: (typeof candidates)[number]) => {
    setError(null);
    try {
      await confirmMutation.mutateAsync({
        candidate_id: candidate.candidate_id,
        category: candidate.category,
        value: candidate.value,
        direction: candidate.direction,
        minimum_evidence: data?.minimum_evidence ?? 2,
      });
    } catch (err) {
      setError(isAppError(err) ? (err as AppError).message : "确认失败，请稍后重试。");
    }
  };

  return (
    <section className="space-y-12">
      <h2 className="text-h2 text-text-primary">
        待确认偏好（{candidates.length}）
      </h2>
      <p className="text-small text-text-secondary">
        这些候选来自你的穿搭反馈，只有你确认后才会写入长期档案。
      </p>

      {error && (
        <p className="rounded-card bg-danger/10 border border-danger/30 px-12 py-8 text-small text-danger" role="alert">
          {error}
        </p>
      )}

      <div className="space-y-12">
        {candidates.map((candidate) => (
          <div
            key={candidate.candidate_id}
            className="rounded-card border border-border bg-surface p-16 space-y-12"
          >
            <div className="flex items-start gap-8">
              <Sparkles size={18} className="text-brand shrink-0 mt-2" aria-hidden="true" />
              <div>
                <p className="text-body text-text-primary">
                  <span className="font-medium">
                    {DIRECTION_LABEL[candidate.direction]}「{candidate.value}」
                  </span>
                  <span className="text-text-secondary">（{candidate.category}）</span>
                </p>
                <p className="text-small text-text-secondary mt-4">
                  来自 {candidate.evidence_count} 次已反馈 Outfit
                  {candidate.opposing_evidence_count > 0
                    ? `，另有 ${candidate.opposing_evidence_count} 条反向证据`
                    : ""}
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-8">
              <span className="px-8 py-4 rounded-tag bg-surface-subtle text-caption text-text-secondary">
                确认后会保存到长期档案
              </span>
              <button
                type="button"
                onClick={() => handleConfirm(candidate)}
                disabled={confirmMutation.isPending}
                className="inline-flex items-center gap-4 px-12 py-6 rounded-input bg-brand text-surface
                           hover:bg-brand-hover disabled:opacity-50 transition-colors text-small"
              >
                <Check size={14} />
                确认
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

import { useState } from "react";
import { History, Trash2, CalendarClock } from "lucide-react";
import {
  usePreferenceMemories,
  useSetPreferenceExpiry,
  useDeletePreferenceMemory,
} from "@/features/style-profile/api";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { isAppError, type AppError } from "@/api/client";
import type { components } from "@/api/generated/schema";

type Memory = components["schemas"]["PreferenceMemoryResponse"];

const DIRECTION_LABEL: Record<string, string> = {
  prefer: "喜欢",
  avoid: "避免",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("zh-CN");
}

/** 偏好来源与有效期 · ui-design §9.4 */
export default function MemoriesList() {
  const { data, isLoading } = usePreferenceMemories();
  const expiryMutation = useSetPreferenceExpiry();
  const deleteMutation = useDeletePreferenceMemory();
  const [deleteTarget, setDeleteTarget] = useState<Memory | null>(null);
  const [error, setError] = useState<string | null>(null);

  const memories = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="rounded-card border border-border bg-surface p-24 animate-pulse space-y-12">
        <div className="h-20 bg-surface-subtle rounded w-1/3" />
        <div className="h-16 bg-surface-subtle rounded w-full" />
      </div>
    );
  }

  if (memories.length === 0) {
    return null;
  }

  const handleSetExpiry = async (memory: Memory) => {
    setError(null);
    try {
      // 简单交互：确认过期的记录点击后恢复长期有效；未过期的设置 90 天后过期
      const expiresAt = memory.expires_at ? null : new Date(Date.now() + 90 * 24 * 3600_000).toISOString();
      await expiryMutation.mutateAsync({ id: memory.preference_memory_id, expiresAt });
    } catch (err) {
      setError(isAppError(err) ? (err as AppError).message : "操作失败");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setError(null);
    try {
      await deleteMutation.mutateAsync(deleteTarget.preference_memory_id);
      setDeleteTarget(null);
    } catch (err) {
      setError(isAppError(err) ? (err as AppError).message : "删除失败");
      setDeleteTarget(null);
    }
  };

  return (
    <section className="space-y-12">
      <div className="flex items-center gap-8">
        <h2 className="text-h2 text-text-primary">偏好来源与有效期</h2>
        <History size={18} className="text-text-secondary" />
      </div>

      {error && (
        <p className="rounded-card bg-danger/10 border border-danger/30 px-12 py-8 text-small text-danger" role="alert">
          {error}
        </p>
      )}

      <div className="rounded-card border border-border bg-surface overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border text-caption text-text-secondary">
              <th className="px-16 py-12 font-normal">偏好</th>
              <th className="px-16 py-12 font-normal hidden md:table-cell">方向</th>
              <th className="px-16 py-12 font-normal hidden md:table-cell">确认时间</th>
              <th className="px-16 py-12 font-normal hidden md:table-cell">有效期</th>
              <th className="px-16 py-12 font-normal text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {memories.map((memory) => (
              <tr key={memory.preference_memory_id} className="border-b border-border last:border-b-0">
                <td className="px-16 py-12">
                  <p className="text-body text-text-primary">{memory.value}</p>
                  <p className="text-caption text-text-secondary md:hidden">
                    {DIRECTION_LABEL[memory.direction]} · {formatDate(memory.confirmed_at)}
                  </p>
                </td>
                <td className="px-16 py-12 hidden md:table-cell">
                  <span className={`text-small ${memory.direction === "prefer" ? "text-success" : "text-danger"}`}>
                    {DIRECTION_LABEL[memory.direction]}
                  </span>
                </td>
                <td className="px-16 py-12 hidden md:table-cell text-caption text-text-secondary">
                  {formatDate(memory.confirmed_at)}
                </td>
                <td className="px-16 py-12 hidden md:table-cell text-caption text-text-secondary">
                  {memory.expires_at ? `至 ${formatDate(memory.expires_at)}` : "长期有效"}
                </td>
                <td className="px-16 py-12">
                  <div className="flex justify-end gap-4">
                    <button
                      type="button"
                      onClick={() => handleSetExpiry(memory)}
                      disabled={expiryMutation.isPending}
                      className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle"
                      title={memory.expires_at ? "恢复长期有效" : "设置 90 天后过期"}
                      aria-label={memory.expires_at ? "恢复长期有效" : "设置过期时间"}
                    >
                      <CalendarClock size={16} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(memory)}
                      className="p-8 rounded-input text-text-secondary hover:bg-danger/10 hover:text-danger"
                      aria-label={`删除偏好 ${memory.value}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {deleteTarget && (
        <ConfirmDialog
          title={`删除「${deleteTarget.value}」这条长期偏好？`}
          description="删除后，它将同时移除该来源对风格档案的影响。此操作无法撤销。"
          confirmLabel="删除偏好"
          busy={deleteMutation.isPending}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </section>
  );
}

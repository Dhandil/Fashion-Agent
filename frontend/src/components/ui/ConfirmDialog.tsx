import { Trash2 } from "lucide-react";

type Props = {
  title: string;
  description: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
};

/** 破坏性操作二次确认对话框 */
export default function ConfirmDialog({
  title,
  description,
  confirmLabel,
  onCancel,
  onConfirm,
  busy = false,
}: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-text-primary/40 p-16"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="w-full max-w-md rounded-card-lg bg-surface p-24 space-y-16 shadow-lg">
        <h3 className="text-h3 text-text-primary">{title}</h3>
        <p className="text-body text-text-secondary">{description}</p>
        <div className="flex justify-end gap-12 pt-8">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="px-16 py-8 rounded-input border border-border text-text-secondary
                       hover:bg-surface-subtle transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="inline-flex items-center gap-8 px-16 py-8 rounded-input bg-danger text-surface
                       hover:opacity-90 disabled:opacity-50 transition-colors"
          >
            <Trash2 size={16} />
            {busy ? "处理中…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

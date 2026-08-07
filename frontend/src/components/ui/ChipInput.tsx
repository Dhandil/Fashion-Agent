import { useState } from "react";
import { X, Plus } from "lucide-react";

type Props = {
  label: string;
  value: string[];
  onChange: (next: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
  /** 与反向列表冲突时提示 */
  conflictWith?: string[];
  /** 冲突标签说明，例如「与避免的颜色冲突」 */
  conflictHint?: string;
  error?: string;
};

/** Chip 字符串数组输入 · ui-design §9.2 */
export default function ChipInput({
  label,
  value,
  onChange,
  suggestions = [],
  placeholder = "输入后回车",
  conflictWith = [],
  conflictHint,
  error,
}: Props) {
  const [text, setText] = useState("");
  const [conflicts, setConflicts] = useState<string[]>([]);

  const add = (raw: string) => {
    const next = raw.trim();
    if (!next || value.includes(next)) return;
    onChange([...value, next]);
  };

  const remove = (v: string) => {
    onChange(value.filter((x) => x !== v));
    setConflicts((c) => c.filter((x) => x !== v));
  };

  const addFromField = () => {
    if (!text.trim()) return;
    add(text);
    setText("");
  };

  const handleSuggestion = (s: string) => {
    if (value.includes(s)) return;
    // 检测与反向列表冲突
    if (conflictWith.includes(s)) {
      setConflicts((c) => (c.includes(s) ? c : [...c, s]));
      return;
    }
    onChange([...value, s]);
  };

  return (
    <div className="space-y-8">
      <span className="text-small text-text-secondary">{label}</span>

      {/* 已保存 Chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-8">
          {value.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => remove(v)}
              className="inline-flex items-center gap-4 rounded-tag bg-surface-subtle px-10 py-4
                         text-small text-text-primary hover:bg-danger/10 hover:text-danger"
              aria-label={`移除 ${v}`}
            >
              {v}
              <X size={12} />
            </button>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-8">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addFromField();
            }
          }}
          onBlur={addFromField}
          placeholder={placeholder}
          aria-label={label}
          className="flex-1 rounded-input border border-border bg-surface px-12 py-8 text-body
                     placeholder:text-text-secondary outline-none focus:border-brand"
        />
        <button
          type="button"
          onClick={addFromField}
          className="p-8 rounded-input border border-border text-text-secondary hover:bg-surface-subtle"
          aria-label={`添加 ${label}`}
        >
          <Plus size={16} />
        </button>
      </div>

      {/* 冲突提示 */}
      {conflicts.length > 0 && (
        <p className="text-small text-danger" role="alert">
          {conflictHint ?? "与反向列表冲突"}：{conflicts.join("、")}
        </p>
      )}
      {error && <p className="text-small text-danger" role="alert">{error}</p>}

      {/* 建议 */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-4">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSuggestion(s)}
              disabled={value.includes(s) || conflictWith.includes(s)}
              className="rounded-tag border border-border px-8 py-2 text-caption text-text-secondary
                         hover:bg-surface-subtle disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

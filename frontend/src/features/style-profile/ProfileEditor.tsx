import { useEffect, useState } from "react";
import type { components } from "@/api/generated/schema";
import ChipInput from "@/components/ui/ChipInput";
import { useStyleProfile, usePatchStyleProfile } from "@/features/style-profile/api";
import { isAppError, type AppError } from "@/api/client";

type StyleProfile = components["schemas"]["StyleProfileResponse"];

const STYLE_SUGGESTIONS = ["简约", "通勤", "休闲", "运动", "复古", "法式", "街头", "正装"];
const COLOR_SUGGESTIONS = ["黑色", "白色", "米白", "灰色", "藏蓝", "卡其", "橄榄绿", "酒红"];
const FIT_SUGGESTIONS = ["宽松", "修身", "直筒", "oversize"];
const MATERIAL_SUGGESTIONS = ["羊毛", "腈纶", "聚酯纤维", "蕾丝"];
const SCENARIO_SUGGESTIONS = ["通勤", "约会", "旅行", "运动", "面试", "日常"];

/** 风格档案编辑器 · ui-design §9.1 + §9.2 */
export default function ProfileEditor() {
  const { data: profile, isLoading, isError } = useStyleProfile();
  const patchMutation = usePatchStyleProfile();

  // 本地编辑状态（PATCH 只提交修改字段）
  const [form, setForm] = useState<StyleProfile | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (profile && !form) {
      setForm(profile);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  // 冲突检测：喜欢/避免同值
  const styleConflicts =
    form?.preferred_styles.filter((s) => form.avoided_styles.includes(s)) ?? [];
  const colorConflicts =
    form?.preferred_colors.filter((c) => form.avoided_colors.includes(c)) ?? [];

  const setField = (key: keyof StyleProfile, value: unknown) => {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setDirty(true);
    setSaved(false);
  };

  const handleSave = async () => {
    if (!form) return;
    setError(null);
    // 冲突拦截（服务端仍会最终校验）
    if (styleConflicts.length > 0 || colorConflicts.length > 0) {
      setError("喜欢的风格/颜色与避免的列表存在冲突，请先移除冲突项。");
      return;
    }
    // 只提交修改字段
    const patch: components["schemas"]["StyleProfilePatchRequest"] = {};
    if (JSON.stringify(form.preferred_styles) !== JSON.stringify(profile?.preferred_styles ?? [])) {
      patch.preferred_styles = form.preferred_styles;
    }
    if (JSON.stringify(form.avoided_styles) !== JSON.stringify(profile?.avoided_styles ?? [])) {
      patch.avoided_styles = form.avoided_styles;
    }
    if (JSON.stringify(form.preferred_colors) !== JSON.stringify(profile?.preferred_colors ?? [])) {
      patch.preferred_colors = form.preferred_colors;
    }
    if (JSON.stringify(form.avoided_colors) !== JSON.stringify(profile?.avoided_colors ?? [])) {
      patch.avoided_colors = form.avoided_colors;
    }
    if (JSON.stringify(form.preferred_fits) !== JSON.stringify(profile?.preferred_fits ?? [])) {
      patch.preferred_fits = form.preferred_fits;
    }
    if (
      JSON.stringify(form.avoided_materials) !== JSON.stringify(profile?.avoided_materials ?? [])
    ) {
      patch.avoided_materials = form.avoided_materials;
    }
    if (
      JSON.stringify(form.common_scenarios) !== JSON.stringify(profile?.common_scenarios ?? [])
    ) {
      patch.common_scenarios = form.common_scenarios;
    }
    if (form.typical_budget_min !== (profile?.typical_budget_min ?? null)) {
      patch.typical_budget_min = form.typical_budget_min;
    }
    if (form.typical_budget_max !== (profile?.typical_budget_max ?? null)) {
      patch.typical_budget_max = form.typical_budget_max;
    }
    if (form.notes !== (profile?.notes ?? null)) {
      patch.notes = form.notes;
    }

    try {
      await patchMutation.mutateAsync(patch);
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(isAppError(err) ? (err as AppError).message : "保存失败，请稍后重试。");
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-card border border-border bg-surface p-24 animate-pulse space-y-16">
        <div className="h-24 bg-surface-subtle rounded w-1/2" />
        <div className="h-16 bg-surface-subtle rounded w-3/4" />
        <div className="h-16 bg-surface-subtle rounded w-2/3" />
      </div>
    );
  }

  if (isError || !form) {
    return (
      <div className="rounded-card border border-danger/30 bg-danger/[0.06] p-24">
        <p className="text-body text-danger">加载风格档案失败，请检查服务是否可用。</p>
      </div>
    );
  }

  return (
    <div className="rounded-card border border-border bg-surface p-24 space-y-24">
      <div>
        <h2 className="text-h2 text-text-primary">我的明确偏好</h2>
        <p className="text-small text-text-secondary mt-8">
          这些偏好由你明确确认，Agent 会优先参考。
        </p>
      </div>

      {/* 状态提示 */}
      {saved && (
        <p className="rounded-card bg-success/10 border border-success/30 px-12 py-8 text-small text-success" role="status">
          已保存
        </p>
      )}
      {error && (
        <p className="rounded-card bg-danger/10 border border-danger/30 px-12 py-8 text-small text-danger" role="alert">
          {error}
        </p>
      )}

      {/* 风格 */}
      <div className="grid md:grid-cols-2 gap-24">
        <ChipInput
          label="喜欢的风格"
          value={form.preferred_styles}
          onChange={(v) => setField("preferred_styles", v)}
          suggestions={STYLE_SUGGESTIONS}
          conflictWith={form.avoided_styles}
          conflictHint="与「避免的风格」冲突"
        />
        <ChipInput
          label="避免的风格"
          value={form.avoided_styles}
          onChange={(v) => setField("avoided_styles", v)}
          suggestions={STYLE_SUGGESTIONS}
          conflictWith={form.preferred_styles}
          conflictHint="与「喜欢的风格」冲突"
        />
      </div>

      {/* 颜色 */}
      <div className="grid md:grid-cols-2 gap-24">
        <ChipInput
          label="喜欢的颜色"
          value={form.preferred_colors}
          onChange={(v) => setField("preferred_colors", v)}
          suggestions={COLOR_SUGGESTIONS}
          conflictWith={form.avoided_colors}
          conflictHint="与「避免的颜色」冲突"
        />
        <ChipInput
          label="避免的颜色"
          value={form.avoided_colors}
          onChange={(v) => setField("avoided_colors", v)}
          suggestions={COLOR_SUGGESTIONS}
          conflictWith={form.preferred_colors}
          conflictHint="与「喜欢的颜色」冲突"
        />
      </div>

      {/* 版型与材质 */}
      <div className="grid md:grid-cols-2 gap-24">
        <ChipInput
          label="版型偏好"
          value={form.preferred_fits}
          onChange={(v) => setField("preferred_fits", v)}
          suggestions={FIT_SUGGESTIONS}
        />
        <ChipInput
          label="避免的材质"
          value={form.avoided_materials}
          onChange={(v) => setField("avoided_materials", v)}
          suggestions={MATERIAL_SUGGESTIONS}
        />
      </div>

      {/* 场景与预算 */}
      <div className="grid md:grid-cols-2 gap-24">
        <ChipInput
          label="常见场景"
          value={form.common_scenarios}
          onChange={(v) => setField("common_scenarios", v)}
          suggestions={SCENARIO_SUGGESTIONS}
        />
        <div className="space-y-16">
          <span className="text-small text-text-secondary">典型预算（元）</span>
          <div className="flex items-center gap-8">
            <input
              type="number"
              min={0}
              value={form.typical_budget_min ?? ""}
              onChange={(e) =>
                setField("typical_budget_min", e.target.value === "" ? null : Number(e.target.value))
              }
              placeholder="最低"
              aria-label="预算下限"
              className="w-24 rounded-input border border-border bg-surface px-12 py-8 text-body outline-none focus:border-brand"
            />
            <span className="text-text-secondary">—</span>
            <input
              type="number"
              min={0}
              value={form.typical_budget_max ?? ""}
              onChange={(e) =>
                setField("typical_budget_max", e.target.value === "" ? null : Number(e.target.value))
              }
              placeholder="最高"
              aria-label="预算上限"
              className="w-24 rounded-input border border-border bg-surface px-12 py-8 text-body outline-none focus:border-brand"
            />
          </div>
        </div>
      </div>

      {/* 备注 */}
      <div className="space-y-4">
        <label htmlFor="profile-notes" className="text-small text-text-secondary">备注（可选）</label>
        <textarea
          id="profile-notes"
          value={form.notes ?? ""}
          onChange={(e) => setField("notes", e.target.value)}
          rows={2}
          placeholder="例如：上班可以接受相对正式的着装"
          className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand resize-none"
        />
      </div>

      {/* 保存 */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty || patchMutation.isPending}
          className="px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover disabled:opacity-50 transition-colors"
        >
          {patchMutation.isPending ? "保存中…" : "保存修改"}
        </button>
      </div>
    </div>
  );
}

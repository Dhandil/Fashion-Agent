import { useEffect, useState } from "react";
import { useForm, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X, Plus, ImageOff } from "lucide-react";
import type { components } from "@/api/generated/schema";

type WardrobeItemStatus = components["schemas"]["WardrobeItemStatus"];
type WardrobeItem = components["schemas"]["WardrobeItemResponse"];

const itemSchema = z.object({
  name: z.string().trim().min(1, "请输入衣物名称").max(100, "名称过长"),
  category: z.string().trim().min(1, "请输入品类"),
  brand: z.string().trim().max(80, "品牌过长").optional().or(z.literal("")),
  colors: z.array(z.string()),
  materials: z.array(z.string()),
  size: z.string().trim().max(40).optional().or(z.literal("")),
  style_tags: z.array(z.string()),
  seasons: z.array(z.string()),
  scenarios: z.array(z.string()),
  image_url: z.string().trim().url("图片地址无效").optional().or(z.literal("")),
  status: z.enum(["available", "unavailable"]),
  notes: z.string().trim().max(500).optional().or(z.literal("")),
});

type FormValues = z.infer<typeof itemSchema>;

const CATEGORY_SUGGESTIONS = ["上装", "下装", "外套", "连衣裙", "鞋履", "配饰"];
const COLOR_SUGGESTIONS = ["白色", "黑色", "米白", "浅蓝", "深蓝", "灰色", "驼色", "绿色"];
const MATERIAL_SUGGESTIONS = ["棉", "亚麻", "羊毛", "牛仔", "真丝", "聚酯纤维"];
const SEASON_SUGGESTIONS = ["春", "夏", "秋", "冬"];
const SCENARIO_SUGGESTIONS = ["通勤", "约会", "旅行", "运动", "日常"];

type Props = {
  open: boolean;
  mode: "create" | "edit";
  item?: WardrobeItem | null;
  onClose: () => void;
  onSubmit: (values: FormValues) => Promise<void>;
};

/** 数组输入：Chip 形式的字符串列表 */
function StringListInput({
  label,
  value,
  onChange,
  suggestions,
  placeholder,
}: {
  label: string;
  value: string[];
  onChange: (next: string[]) => void;
  suggestions: string[];
  placeholder: string;
}) {
  const [draftValue, setDraftValue] = useState("");
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const addSuggestion = (s: string) => {
    const normalized = s.trim();
    if (normalized && !value.includes(normalized)) {
      onChange([...value, normalized]);
    }
    setDraftValue("");
  };

  return (
    <div className="space-y-8">
      <span className="text-small text-text-secondary">{label}</span>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-8">
          {value.map((v, i) => (
            <button
              key={`${v}-${i}`}
              type="button"
              onClick={() => remove(i)}
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
      <input
        type="text"
        value={draftValue}
        onChange={(event) => setDraftValue(event.target.value)}
        placeholder={placeholder}
        onKeyDown={(e) => {
          if (e.key === "Enter" && draftValue.trim()) {
            e.preventDefault();
            addSuggestion(draftValue);
          }
        }}
        onBlur={() => {
          if (draftValue.trim()) {
            addSuggestion(draftValue);
          }
        }}
        className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body
                   placeholder:text-text-secondary outline-none focus:border-brand"
      />
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-4">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => addSuggestion(s)}
              className="rounded-tag border border-border px-8 py-2 text-caption text-text-secondary
                         hover:bg-surface-subtle transition-colors"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WardrobeFormDrawer({ open, mode, item, onClose, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      name: "",
      category: "",
      brand: "",
      colors: [],
      materials: [],
      size: "",
      style_tags: [],
      seasons: [],
      scenarios: [],
      image_url: "",
      status: "available",
      notes: "",
    },
  });

  // 打开时重置表单
  useEffect(() => {
    if (open) {
      reset({
        name: item?.name ?? "",
        category: item?.category ?? "",
        brand: item?.brand ?? "",
        colors: item?.colors ?? [],
        materials: item?.materials ?? [],
        size: item?.size ?? "",
        style_tags: item?.style_tags ?? [],
        seasons: item?.seasons ?? [],
        scenarios: item?.scenarios ?? [],
        image_url: item?.image_url ?? "",
        status: item?.status ?? "available",
        notes: item?.notes ?? "",
      });
    }
  }, [open, item, reset]);

  if (!open) return null;

  const imageUrl = watch("image_url");

  const submitHandler: SubmitHandler<FormValues> = async (values) => {
    // 可选字段保持 undefined，避免把空串写入后端；PATCH 只提交变化字段
    await onSubmit(values);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-text-primary/40">
      <div className="w-full max-w-xl h-full bg-canvas overflow-y-auto" role="dialog" aria-modal="true" aria-label={mode === "create" ? "新增衣物" : "编辑衣物"}>
        <div className="flex items-center justify-between px-24 py-16 bg-surface border-b border-border sticky top-0">
          <h2 className="text-h2 text-text-primary">{mode === "create" ? "新增衣物" : "编辑衣物"}</h2>
          <button type="button" onClick={onClose} className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle" aria-label="关闭">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(submitHandler)} className="p-24 space-y-24">
          {/* 分组 1：名称和品类 */}
          <section className="space-y-16">
            <h3 className="text-h3 text-text-primary">基本信息</h3>
            <div className="space-y-4">
              <label htmlFor="name" className="text-small text-text-secondary">名称 *</label>
              <input
                id="name"
                type="text"
                {...register("name")}
                placeholder="例如：浅蓝色亚麻衬衫"
                className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand"
              />
              {errors.name && <p className="text-small text-danger" role="alert">{errors.name.message}</p>}
            </div>
            <div className="space-y-4">
              <label htmlFor="category" className="text-small text-text-secondary">品类 *</label>
              <input
                id="category"
                type="text"
                {...register("category")}
                list="category-list"
                placeholder="例如：上装、下装、鞋履"
                className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand"
              />
              <datalist id="category-list">
                {CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
              </datalist>
              {errors.category && <p className="text-small text-danger" role="alert">{errors.category.message}</p>}
            </div>
            <div className="space-y-4">
              <label htmlFor="brand" className="text-small text-text-secondary">品牌（可选）</label>
              <input id="brand" type="text" {...register("brand")} placeholder="不记得可以留空"
                className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand" />
            </div>
          </section>

          {/* 分组 2：图片 */}
          <section className="space-y-12">
            <h3 className="text-h3 text-text-primary">图片</h3>
            <div className="flex items-start gap-16">
              <div className="w-24 h-30 shrink-0 aspect-[4/5] rounded-card bg-surface-subtle border border-border flex items-center justify-center overflow-hidden">
                {imageUrl ? (
                  <img src={imageUrl} alt="衣物预览" className="w-full h-full object-cover" />
                ) : (
                  <ImageOff size={24} className="text-text-secondary" />
                )}
              </div>
              <div className="flex-1 space-y-4">
                <label htmlFor="image_url" className="text-small text-text-secondary">图片地址（可选）</label>
                <input id="image_url" type="url" {...register("image_url")} placeholder="https://…"
                  className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand" />
                {errors.image_url && <p className="text-small text-danger" role="alert">{errors.image_url.message}</p>}
              </div>
            </div>
          </section>

          {/* 分组 3：颜色、材质和尺码 */}
          <section className="space-y-16">
            <h3 className="text-h3 text-text-primary">外观与尺码</h3>
            <StringListInput
              label="颜色"
              value={watch("colors")}
              onChange={(v) => setValue("colors", v)}
              suggestions={COLOR_SUGGESTIONS}
              placeholder="输入颜色后回车"
            />
            <StringListInput
              label="材质"
              value={watch("materials")}
              onChange={(v) => setValue("materials", v)}
              suggestions={MATERIAL_SUGGESTIONS}
              placeholder="输入材质后回车"
            />
            <div className="space-y-4">
              <label htmlFor="size" className="text-small text-text-secondary">尺码（可选）</label>
              <input id="size" type="text" {...register("size")} placeholder="例如：M、170/92A、42"
                className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand" />
            </div>
          </section>

          {/* 分组 4：风格、季节和场景 */}
          <section className="space-y-16">
            <h3 className="text-h3 text-text-primary">风格与场景</h3>
            <StringListInput
              label="风格标签"
              value={watch("style_tags")}
              onChange={(v) => setValue("style_tags", v)}
              suggestions={[]}
              placeholder="输入风格后回车，例如：简约、通勤"
            />
            <StringListInput
              label="适用季节"
              value={watch("seasons")}
              onChange={(v) => setValue("seasons", v)}
              suggestions={SEASON_SUGGESTIONS}
              placeholder="输入季节后回车"
            />
            <StringListInput
              label="适用场景"
              value={watch("scenarios")}
              onChange={(v) => setValue("scenarios", v)}
              suggestions={SCENARIO_SUGGESTIONS}
              placeholder="输入场景后回车"
            />
          </section>

          {/* 分组 5：状态和备注 */}
          <section className="space-y-16">
            <h3 className="text-h3 text-text-primary">状态</h3>
            <div className="flex gap-16">
              {(["available", "unavailable"] as WardrobeItemStatus[]).map((s) => (
                <label key={s} className="flex items-center gap-8 cursor-pointer">
                  <input type="radio" {...register("status")} value={s} className="accent-brand" />
                  <span className="text-body text-text-primary">
                    {s === "available" ? "可用" : "暂不可用"}
                  </span>
                </label>
              ))}
            </div>
            <div className="space-y-4">
              <label htmlFor="notes" className="text-small text-text-secondary">备注（可选）</label>
              <textarea id="notes" {...register("notes")} rows={2} placeholder="例如：待洗、未干、损坏…"
                className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand resize-none" />
            </div>
          </section>

          {/* 提交 */}
          <div className="flex justify-end gap-12 pt-8 border-t border-border sticky bottom-0 bg-canvas py-16">
            <button type="button" onClick={onClose} className="px-16 py-8 rounded-input border border-border text-text-secondary hover:bg-surface-subtle transition-colors">
              取消
            </button>
            <button type="submit" disabled={isSubmitting}
              className="inline-flex items-center gap-8 px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover disabled:opacity-50 transition-colors">
              <Plus size={16} />
              {isSubmitting ? "保存中…" : mode === "create" ? "加入衣橱" : "保存修改"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export type { FormValues as WardrobeFormValues };

import { useRef, useState } from "react";
import { X, Upload, Scan, AlertTriangle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  completeWardrobeImageUpload,
  createWardrobeImageUpload,
    recognizeWardrobeImage,
  uploadWardrobeImage,
  validateWardrobeImageFile,
  readFileAsDataUrl,
  useCreateWardrobeItem,
} from "@/features/wardrobe/api";
import ChipInput from "@/components/ui/ChipInput";
import { isAppError, type AppError } from "@/api/client";
import type { components } from "@/api/generated/schema";

type Draft = components["schemas"]["WardrobeItemDraftResponse"];

type Props = {
  open: boolean;
  onClose: () => void;
};

const FIELD_LABELS: Record<string, string> = {
  name: "名称",
  category: "品类",
  colors: "颜色",
  materials: "材质",
  style_tags: "风格",
  seasons: "季节",
  scenarios: "场景",
};

/** 图片识别两阶段确认 · ui-design §7.4 / frontend §6.3 */
export default function WardrobeImageRecognitionDrawer({ open, onClose }: Props) {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const createMutation = useCreateWardrobeItem();

  // 阶段 1：选图与预览
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [imageAssetId, setImageAssetId] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // 阶段 2：识别结果草稿（可编辑）
  const [draft, setDraft] = useState<Draft | null>(null);
  const [recognizing, setRecognizing] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  if (!open) return null;

  const reset = () => {
    setPreviewUrl(null);
    setFileName(null);
    setImageAssetId(null);
    setFileError(null);
    setDraft(null);
    setRecognizing(false);
    setPageError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFileChange = async (file: File | undefined) => {
    if (!file) return;
    setFileError(null);
    setPageError(null);

    const err = validateWardrobeImageFile(file);
    if (err) {
      setFileError(err);
      setPreviewUrl(null);
      setDraft(null);
      return;
    }

    const dataUrl = await readFileAsDataUrl(file);
    setPreviewUrl(dataUrl);
    setFileName(file.name);
    setDraft(null);

    // 先直传到本地文件卷，再用资产 ID 发起识别，避免 Base64 放大请求体。
    setRecognizing(true);
    try {
      const upload = await createWardrobeImageUpload({
        contentType: file.type as components["schemas"]["WardrobeImageContentType"],
        byteSize: file.size,
      });
      await uploadWardrobeImage(upload.upload_url, file);
      const completed = await completeWardrobeImageUpload(upload.image_asset_id);
      setImageAssetId(completed.image_asset_id);
      const result = await recognizeWardrobeImage({
        imageAssetId: completed.image_asset_id,
      });
      setDraft(result);
    } catch (err) {
      setPageError(
        isAppError(err)
          ? (err as AppError).message
          : "识别失败，请稍后重试或手动录入。",
      );
    } finally {
      setRecognizing(false);
    }
  };

  const setDraftField = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  };

  const handleConfirm = async () => {
    if (!draft) return;
    if (!draft.name?.trim() || !draft.category?.trim()) {
      setPageError("名称和品类为必填项，请补充后再确认。");
      return;
    }
    setPageError(null);
    try {
      await createMutation.mutateAsync({
        name: draft.name!.trim(),
        category: draft.category!.trim(),
        brand: null,
        colors: draft.colors,
        materials: draft.materials,
        size: null,
        style_tags: draft.style_tags,
        seasons: draft.seasons,
        scenarios: draft.scenarios,
        image_url: draft.image_url ?? null,
        image_asset_id: draft.image_asset_id ?? imageAssetId,
        status: "available",
        notes: draft.notes ?? null,
      });
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
      handleClose();
    } catch (err) {
      setPageError(isAppError(err) ? (err as AppError).message : "保存失败，请稍后重试。");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-text-primary/40">
      <div className="w-full max-w-2xl h-full bg-canvas overflow-y-auto" role="dialog" aria-modal="true" aria-label="拍照识别衣物">
        {/* 头部 */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-24 py-16 bg-surface border-b border-border">
          <h2 className="text-h2 text-text-primary">拍照识别衣物</h2>
          <button type="button" onClick={handleClose} className="p-8 rounded-input text-text-secondary hover:bg-surface-subtle" aria-label="关闭">
            <X size={20} />
          </button>
        </div>

        <div className="p-24 space-y-24">
          {/* 错误提示 */}
          {fileError && (
            <p className="rounded-card bg-danger/10 border border-danger/30 px-16 py-12 text-small text-danger" role="alert">
              {fileError}
            </p>
          )}
          {pageError && (
            <p className="rounded-card bg-danger/10 border border-danger/30 px-16 py-12 text-small text-danger" role="alert">
              {pageError}
            </p>
          )}

          {/* 选图区 */}
          <div
            className="rounded-card border-2 border-dashed border-border p-24 text-center cursor-pointer hover:border-brand/40 transition-colors"
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0])}
              aria-label="选择衣物照片"
            />
            {previewUrl ? (
              <div className="flex items-center justify-center gap-16">
                <img
                  src={previewUrl}
                  alt={fileName ?? "衣物预览"}
                  className="w-24 h-30 object-cover rounded-card border border-border"
                />
                <div className="text-left">
                  <p className="text-body text-text-primary">{fileName}</p>
                  <p className="text-small text-text-secondary mt-4">点击重新选择</p>
                </div>
              </div>
            ) : (
              <div className="space-y-8">
                <Upload size={28} className="mx-auto text-text-secondary" />
                <p className="text-body text-text-primary">选择衣物照片</p>
                <p className="text-small text-text-secondary">JPEG / PNG · 不超过 5MB</p>
              </div>
            )}
          </div>

          {/* 识别中 */}
          {recognizing && (
            <div className="flex items-center gap-8 rounded-card bg-surface-subtle px-16 py-12" aria-live="polite">
              <Scan size={18} className="text-brand animate-pulse" />
              <span className="text-small text-text-secondary">正在识别衣物特征…</span>
            </div>
          )}

          {/* 草稿编辑 */}
          {draft && !recognizing && (
            <div className="space-y-20">
              {/* 不确定字段提示 */}
              {draft.uncertain_fields.length > 0 && (
                <div className="rounded-card bg-warning/10 border border-warning/30 px-16 py-12">
                  <p className="flex items-center gap-8 text-small text-warning font-medium">
                    <AlertTriangle size={16} />
                    这些字段需要你确认
                  </p>
                  <p className="text-small text-text-secondary mt-4">
                    {draft.uncertain_fields.map((f) => FIELD_LABELS[f] ?? f).join("、")}
                    {draft.missing_fields.length > 0 &&
                      `；未识别字段：${draft.missing_fields.map((f) => FIELD_LABELS[f] ?? f).join("、")}`}
                  </p>
                </div>
              )}

              <div className="space-y-16">
                {/* 名称与品类 */}
                <div className="grid md:grid-cols-2 gap-16">
                  <div className="space-y-4">
                    <label htmlFor="draft-name" className="text-small text-text-secondary">名称 *</label>
                    <input
                      id="draft-name"
                      type="text"
                      value={draft.name ?? ""}
                      onChange={(e) => setDraftField("name", e.target.value)}
                      placeholder="识别不到时需要补充"
                      className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand"
                    />
                  </div>
                  <div className="space-y-4">
                    <label htmlFor="draft-category" className="text-small text-text-secondary">品类 *</label>
                    <input
                      id="draft-category"
                      type="text"
                      value={draft.category ?? ""}
                      onChange={(e) => setDraftField("category", e.target.value)}
                      placeholder="例如：衬衫、长裤、鞋履"
                      className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body placeholder:text-text-secondary outline-none focus:border-brand"
                    />
                  </div>
                </div>

                {/* 颜色与材质 */}
                <div className="grid md:grid-cols-2 gap-16">
                  <ChipInput
                    label="颜色"
                    value={draft.colors}
                    onChange={(v) => setDraftField("colors", v)}
                    placeholder="输入颜色后回车"
                  />
                  <ChipInput
                    label="材质"
                    value={draft.materials}
                    onChange={(v) => setDraftField("materials", v)}
                    placeholder="输入材质后回车"
                  />
                </div>

                {/* 风格与季节 */}
                <div className="grid md:grid-cols-2 gap-16">
                  <ChipInput
                    label="风格"
                    value={draft.style_tags}
                    onChange={(v) => setDraftField("style_tags", v)}
                    placeholder="输入风格后回车"
                  />
                  <ChipInput
                    label="季节"
                    value={draft.seasons}
                    onChange={(v) => setDraftField("seasons", v)}
                    placeholder="输入季节后回车"
                  />
                </div>

                {/* 场景与备注 */}
                <div className="grid md:grid-cols-2 gap-16">
                  <ChipInput
                    label="场景"
                    value={draft.scenarios}
                    onChange={(v) => setDraftField("scenarios", v)}
                    placeholder="输入场景后回车"
                  />
                  <div className="space-y-4">
                    <label htmlFor="draft-notes" className="text-small text-text-secondary">备注</label>
                    <input
                      id="draft-notes"
                      type="text"
                      value={draft.notes ?? ""}
                      onChange={(e) => setDraftField("notes", e.target.value)}
                      className="w-full rounded-input border border-border bg-surface px-12 py-8 text-body outline-none focus:border-brand"
                    />
                  </div>
                </div>

                {/* 置信度 */}
                <p className="text-caption text-text-secondary">
                  识别置信度：{Math.round(draft.confidence * 100)}%
                  {draft.requires_confirmation ? " · 需要确认后才能加入衣橱" : ""}
                </p>
              </div>

              {/* 操作 */}
              <div className="flex justify-end gap-12 pt-4 border-t border-border sticky bottom-0 bg-canvas py-16">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-16 py-8 rounded-input border border-border text-text-secondary hover:bg-surface-subtle transition-colors"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={createMutation.isPending}
                  className="px-16 py-8 rounded-input bg-brand text-surface hover:bg-brand-hover disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? "保存中…" : "确认并加入衣橱"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

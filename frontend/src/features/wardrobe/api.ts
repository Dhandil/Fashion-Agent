/**
 * 衣橱 API hooks · frontend §9
 * Query Keys: ['wardrobe', filters] / ['wardrobe-item', id]
 */

import { useEffect, useState } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/generated/schema";

type WardrobeItem = components["schemas"]["WardrobeItemResponse"];
type WardrobeItemList = components["schemas"]["WardrobeItemListResponse"];

export type WardrobeFilters = {
  category?: string | null;
  status?: "available" | "unavailable" | null;
  limit?: number;
  offset?: number;
};

const PAGE_SIZE = 12;

export const wardrobeQueryKeys = {
  list: (filters: WardrobeFilters) => ["wardrobe", filters] as const,
  detail: (id: string) => ["wardrobe-item", id] as const,
};

export function useWardrobeList(filters: WardrobeFilters) {
  return useQuery({
    queryKey: wardrobeQueryKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.category) params.set("category", filters.category);
      if (filters.status) params.set("status", filters.status);
      params.set("limit", String(filters.limit ?? PAGE_SIZE));
      params.set("offset", String(filters.offset ?? 0));
      const qs = params.toString();
      return api.get<WardrobeItemList>(`/wardrobe${qs ? `?${qs}` : ""}`);
    },
  });
}

export function useWardrobeItem(id: string | null) {
  return useQuery({
    queryKey: wardrobeQueryKeys.detail(id ?? ""),
    queryFn: () => api.get<WardrobeItem>(`/wardrobe/${id}`),
    enabled: !!id,
  });
}

export function useCreateWardrobeItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: components["schemas"]["WardrobeItemCreate"]) =>
      api.post<WardrobeItem>("/wardrobe", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
  });
}

export function useUpdateWardrobeItem(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: components["schemas"]["WardrobeItemPatch"]) =>
      api.patch<WardrobeItem>(`/wardrobe/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
      qc.invalidateQueries({ queryKey: ["wardrobe-item", id] });
    },
  });
}

export function useUpdateWardrobeStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: components["schemas"]["WardrobeItemStatus"];
    }) =>
      api.patch<WardrobeItem>(`/wardrobe/${id}/status`, { status }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
      qc.invalidateQueries({ queryKey: ["wardrobe-item", vars.id] });
    },
  });
}

export function useDeleteWardrobeItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/wardrobe/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
  });
}

export const WARDROBE_PAGE_SIZE = PAGE_SIZE;

/** 鐢ㄥ甫韬唤鐨 API 璇诲彇绉佹湁鍥剧墖锛屽苟杩斿洖涓存椂 Object URL。 */
export function useWardrobeImageUrl(imageUrl: string | null | undefined): {
  resolvedUrl: string | null;
  isLoading: boolean;
} {
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(imageUrl));

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    if (!imageUrl) {
      setResolvedUrl(null);
      setIsLoading(false);
      return () => {
        active = false;
      };
    }

    // 旧数据可能仍是外部托管 URL；只有本地私有图片需要带身份读取 Blob。
    if (!imageUrl.startsWith("/api/v1/wardrobe/images/")) {
      setResolvedUrl(imageUrl);
      setIsLoading(false);
      return () => {
        active = false;
      };
    }

    setResolvedUrl(null);
    setIsLoading(true);
    void api.getBlob(imageUrl).then(
      (blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) {
          setResolvedUrl(objectUrl);
          setIsLoading(false);
        } else {
          URL.revokeObjectURL(objectUrl);
        }
      },
      () => {
        if (active) {
          setResolvedUrl(null);
          setIsLoading(false);
        }
      },
    );

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [imageUrl]);

  return { resolvedUrl, isLoading };
}

// ── 图片识别 · frontend §6.3 ──

type DraftResponse = components["schemas"]["WardrobeItemDraftResponse"];

type ImageUploadResponse = components["schemas"]["WardrobeImageUploadResponse"];

export type WardrobeBatchRecognitionFailure = {
  image_asset_id: string;
  code: string;
  message: string;
};

export type WardrobeBatchRecognitionResponse = {
  items: DraftResponse[];
  failures: WardrobeBatchRecognitionFailure[];
};

/** 创建本地图片上传凭证。 */
export function createWardrobeImageUpload(input: {
  contentType: components["schemas"]["WardrobeImageContentType"];
  byteSize: number;
}): Promise<ImageUploadResponse> {
  return api.post<ImageUploadResponse>("/wardrobe/images/uploads", {
    content_type: input.contentType,
    byte_size: input.byteSize,
  });
}

/** 将图片原始字节直传到本地文件卷。 */
export async function uploadWardrobeImage(
  uploadUrl: string,
  file: File,
): Promise<void> {
  await api.putBinary<void>(uploadUrl, file, file.type);
}

/** 确认图片上传完成并取得资产摘要。 */
export function completeWardrobeImageUpload(
  imageAssetId: string,
): Promise<components["schemas"]["WardrobeImageAssetResponse"]> {
  return api.post<components["schemas"]["WardrobeImageAssetResponse"]>(
    `/wardrobe/images/${encodeURIComponent(imageAssetId)}/complete`,
  );
}

/** 识别一张衣物照片，返回待确认草稿 */
export async function recognizeWardrobeImage(input: {
  imageBase64?: string;
  imageAssetId?: string;
  contentType?: components["schemas"]["WardrobeImageContentType"];
  hint?: string | null;
}): Promise<DraftResponse> {
  return api.post<DraftResponse>("/wardrobe/recognitions", {
    image_base64: input.imageBase64,
    image_asset_id: input.imageAssetId,
    content_type: input.contentType,
    hint: input.hint ?? null,
  });
}

/** 批量识别已完成上传的图片；单张失败不会阻断其他草稿。 */
export function recognizeWardrobeImagesBatch(input: {
  imageAssetIds: string[];
  hint?: string | null;
}): Promise<WardrobeBatchRecognitionResponse> {
  return api.post<WardrobeBatchRecognitionResponse>(
    "/wardrobe/recognitions/batch",
    {
      image_asset_ids: input.imageAssetIds,
      hint: input.hint ?? null,
    },
  );
}

/**
 * 客户端图片校验：格式 + 大小
 * 注意：当前视觉 Provider（GLM-4V-Flash）仅支持 JPEG/PNG，
 * 格式白名单必须与 Provider 能力一致（见 docs/roadmap 图片识别限制）。
 */
export const WARDROBE_IMAGE_MAX_BYTES = 5 * 1024 * 1024;
export const WARDROBE_BATCH_IMAGE_MAX_COUNT = 5;

export function validateWardrobeImageFile(file: File): string | null {
  const allowed = new Set([
    "image/jpeg",
    "image/png",
  ]);
  if (!allowed.has(file.type)) {
    return "当前识别模型仅支持 JPEG 或 PNG 格式的图片。";
  }
  if (file.size > WARDROBE_IMAGE_MAX_BYTES) {
    return "图片不能超过 5MB。";
  }
  return null;
}

/** 批量上传图片并提交批量识别，返回逐图片草稿和失败摘要。 */
export async function uploadAndRecognizeWardrobeImages(
  files: File[],
  hint?: string | null,
): Promise<WardrobeBatchRecognitionResponse> {
  if (files.length === 0) {
    throw new Error("请至少选择一张衣物照片。");
  }
  if (files.length > WARDROBE_BATCH_IMAGE_MAX_COUNT) {
    throw new Error(`一次最多选择 ${WARDROBE_BATCH_IMAGE_MAX_COUNT} 张照片。`);
  }

  const imageAssetIds: string[] = [];
  for (const file of files) {
    const validationError = validateWardrobeImageFile(file);
    if (validationError) throw new Error(validationError);
    const upload = await createWardrobeImageUpload({
      contentType: file.type as components["schemas"]["WardrobeImageContentType"],
      byteSize: file.size,
    });
    await uploadWardrobeImage(upload.upload_url, file);
    const completed = await completeWardrobeImageUpload(upload.image_asset_id);
    imageAssetIds.push(completed.image_asset_id);
  }
  return recognizeWardrobeImagesBatch({ imageAssetIds, hint });
}

/** 读取文件为 Data URL */
export function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("无法读取图片文件"));
    reader.readAsDataURL(file);
  });
}

/** 从 Data URL 提取纯 Base64 */
export function stripDataUrlPrefix(dataUrl: string): string {
  return dataUrl.split(",")[1] ?? dataUrl;
}

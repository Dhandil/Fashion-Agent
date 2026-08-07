/**
 * 衣橱 API hooks · frontend §9
 * Query Keys: ['wardrobe', filters] / ['wardrobe-item', id]
 */

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

// ── 图片识别 · frontend §6.3 ──

type DraftResponse = components["schemas"]["WardrobeItemDraftResponse"];

/** 识别一张衣物照片，返回待确认草稿 */
export async function recognizeWardrobeImage(input: {
  imageBase64: string;
  contentType: components["schemas"]["WardrobeImageContentType"];
  hint?: string | null;
}): Promise<DraftResponse> {
  return api.post<DraftResponse>("/wardrobe/recognitions", {
    image_base64: input.imageBase64,
    content_type: input.contentType,
    hint: input.hint ?? null,
  });
}

/**
 * 客户端图片校验：格式 + 大小
 * 注意：当前视觉 Provider（GLM-4V-Flash）仅支持 JPEG/PNG，
 * 格式白名单必须与 Provider 能力一致（见 docs/roadmap 图片识别限制）。
 */
export const WARDROBE_IMAGE_MAX_BYTES = 5 * 1024 * 1024;

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

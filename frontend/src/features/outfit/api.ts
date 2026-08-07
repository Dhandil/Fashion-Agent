/**
 * Outfit API hooks · frontend §9
 * Query Keys: ['outfits', filters] / ['outfit', id] / ['outfit-feedback', id]
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/generated/schema";

type OutfitResponse = components["schemas"]["OutfitResponse"];
type OutfitListResponse = components["schemas"]["OutfitListResponse"];
type FeedbackResponse = components["schemas"]["OutfitFeedbackResponse"];

export type OutfitFilters = {
  scenario?: string | null;
  favorite_only?: boolean;
  limit?: number;
  offset?: number;
};

const PAGE_SIZE = 12;

export const outfitQueryKeys = {
  list: (filters: OutfitFilters) => ["outfits", filters] as const,
  detail: (id: string) => ["outfit", id] as const,
  feedback: (id: string) => ["outfit-feedback", id] as const,
};

export function useOutfitList(filters: OutfitFilters) {
  return useQuery({
    queryKey: outfitQueryKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.scenario) params.set("scenario", filters.scenario);
      if (filters.favorite_only) params.set("favorite_only", "true");
      params.set("limit", String(filters.limit ?? PAGE_SIZE));
      params.set("offset", String(filters.offset ?? 0));
      const qs = params.toString();
      return api.get<OutfitListResponse>(`/outfits${qs ? `?${qs}` : ""}`);
    },
  });
}

export function useOutfitDetail(id: string | null) {
  return useQuery({
    queryKey: outfitQueryKeys.detail(id ?? ""),
    queryFn: () => api.get<OutfitResponse>(`/outfits/${id}`),
    enabled: !!id,
  });
}

export function useOutfitFeedback(id: string | null) {
  return useQuery({
    queryKey: outfitQueryKeys.feedback(id ?? ""),
    queryFn: () => api.get<FeedbackResponse>(`/outfits/${id}/feedback`),
    enabled: !!id,
  });
}

export function useSetOutfitFavorite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isFavorite }: { id: string; isFavorite: boolean }) =>
      api.patch<OutfitResponse>(`/outfits/${id}/favorite`, {
        is_favorite: isFavorite,
      } satisfies components["schemas"]["OutfitFavoriteUpdate"]),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["outfits"] });
      qc.invalidateQueries({ queryKey: ["outfit", vars.id] });
    },
  });
}

export function useUpsertOutfitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: components["schemas"]["OutfitFeedbackUpsertRequest"];
    }) => api.put<FeedbackResponse>(`/outfits/${id}/feedback`, body),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["outfit-feedback", vars.id] });
      qc.invalidateQueries({ queryKey: ["recent-feedback"] });
      qc.invalidateQueries({ queryKey: ["preference-candidates"] });
    },
  });
}

export function useDeleteOutfitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/outfits/${id}/feedback`),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["outfit-feedback", id] });
      qc.invalidateQueries({ queryKey: ["recent-feedback"] });
      qc.invalidateQueries({ queryKey: ["preference-candidates"] });
    },
  });
}

export const OUTFIT_PAGE_SIZE = PAGE_SIZE;

// ── 商品目录 · 辅助购物 ──

type ProductListResponse = components["schemas"]["ProductListResponse"];

export type ProductSearchParams = {
  query?: string;
  category?: string;
  maxPrice?: number;
  limit?: number;
};

export function useProductSearch(params: ProductSearchParams, enabled = true) {
  return useQuery({
    queryKey: ["products", params],
    enabled,
    queryFn: async () => {
      const p = new URLSearchParams();
      if (params.query) p.set("query", params.query);
      if (params.category) p.set("category", params.category);
      if (params.maxPrice !== undefined) p.set("max_price", String(params.maxPrice));
      p.set("limit", String(params.limit ?? 5));
      const qs = p.toString();
      return api.get<ProductListResponse>(`/products${qs ? `?${qs}` : ""}`);
    },
  });
}

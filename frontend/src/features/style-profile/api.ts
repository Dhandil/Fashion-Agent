/**
 * 风格档案 API hooks · frontend §9
 * Query Keys: ['style-profile'] / ['preference-candidates'] / ['preference-memories']
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import type { components } from "@/api/generated/schema";

type StyleProfile = components["schemas"]["StyleProfileResponse"];
type CandidateList = components["schemas"]["PreferenceCandidateListResponse"];
type MemoryList = components["schemas"]["PreferenceMemoryListResponse"];
type PreferenceMemory = components["schemas"]["PreferenceMemoryResponse"];

export const profileQueryKeys = {
  profile: () => ["style-profile"] as const,
  candidates: (minimumEvidence?: number) =>
    ["preference-candidates", minimumEvidence] as const,
  memories: (includeExpired?: boolean) =>
    ["preference-memories", includeExpired] as const,
};

export function useStyleProfile() {
  return useQuery({
    queryKey: profileQueryKeys.profile(),
    queryFn: () => api.get<StyleProfile>("/style-profile"),
  });
}

export function usePreferenceCandidates(minimumEvidence?: number) {
  return useQuery({
    queryKey: profileQueryKeys.candidates(minimumEvidence),
    queryFn: async () => {
      const qs = minimumEvidence ? `?minimum_evidence=${minimumEvidence}` : "";
      return api.get<CandidateList>(`/style-profile/candidates${qs}`);
    },
  });
}

export function usePreferenceMemories(includeExpired?: boolean) {
  return useQuery({
    queryKey: profileQueryKeys.memories(includeExpired),
    queryFn: async () => {
      const qs = includeExpired ? "?include_expired=true" : "";
      return api.get<MemoryList>(`/style-profile/memories${qs}`);
    },
  });
}

/** 局部修改档案 · 只提交实际修改字段 */
export function usePatchStyleProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: components["schemas"]["StyleProfilePatchRequest"]) =>
      api.patch<StyleProfile>("/style-profile", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["style-profile"] });
    },
  });
}

export function useConfirmCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: components["schemas"]["PreferenceCandidateConfirmRequest"]) =>
      api.post<StyleProfile>("/style-profile/candidates/confirm", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["style-profile"] });
      qc.invalidateQueries({ queryKey: ["preference-candidates"] });
      qc.invalidateQueries({ queryKey: ["preference-memories"] });
    },
  });
}

export function useSetPreferenceExpiry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      expiresAt,
    }: {
      id: string;
      expiresAt: string | null;
    }) =>
      api.patch<PreferenceMemory>(`/style-profile/memories/${id}`, {
        expires_at: expiresAt,
      } satisfies components["schemas"]["PreferenceMemoryExpiryRequest"]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["preference-memories"] });
      qc.invalidateQueries({ queryKey: ["style-profile"] });
    },
  });
}

export function useDeletePreferenceMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/style-profile/memories/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["preference-memories"] });
      qc.invalidateQueries({ queryKey: ["style-profile"] });
      qc.invalidateQueries({ queryKey: ["preference-candidates"] });
    },
  });
}

export function useDeleteStyleProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete<void>("/style-profile"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["style-profile"] });
      qc.invalidateQueries({ queryKey: ["preference-candidates"] });
      qc.invalidateQueries({ queryKey: ["preference-memories"] });
    },
  });
}

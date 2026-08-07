import { useEffect, useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, Activity, Trash2 } from "lucide-react";
import { api, isAppError, type AppError } from "@/api/client";
import { useDeleteStyleProfile } from "@/features/style-profile/api";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

type HealthStatus = {
  status: string;
  app_name: string;
  environment: string;
};

export default function SettingsPage() {
  const qc = useQueryClient();
  const deleteProfileMutation = useDeleteStyleProfile();

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setHealthError(null);
    try {
      // 健康检查是公开端点，不携带也不要求用户身份
      const data = await api.get<HealthStatus>("/health", { anonymous: true });
      setHealth(data);
    } catch (err) {
      setHealthError(isAppError(err) ? (err as AppError).message : "无法获取服务状态");
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  const handleClearProfile = async () => {
    setPageError(null);
    try {
      await deleteProfileMutation.mutateAsync();
      // 清除与该用户相关的所有缓存
      qc.clear();
      setConfirmOpen(false);
    } catch (err) {
      setPageError(isAppError(err) ? (err as AppError).message : "清除失败，请稍后重试。");
      setConfirmOpen(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-16 md:px-32 py-24">
      <div className="max-w-content mx-auto space-y-24">
        <div>
          <h1 className="text-h1 text-text-primary">设置与隐私</h1>
          <p className="text-small text-text-secondary mt-8">管理会话、数据和隐私偏好。</p>
        </div>

        {pageError && (
          <p className="rounded-card bg-danger/10 border border-danger/30 px-16 py-12 text-small text-danger" role="alert">
            {pageError}
          </p>
        )}

        {/* 服务状态 */}
        <section className="rounded-card border border-border bg-surface p-20 space-y-12">
          <h2 className="text-h2 text-text-primary flex items-center gap-8">
            <Activity size={18} className="text-brand" />
            服务状态
          </h2>
          {healthError ? (
            <div className="flex items-center gap-8">
              <p className="text-small text-danger" role="alert">{healthError}</p>
              <button
                type="button"
                onClick={loadHealth}
                className="text-small text-brand underline"
              >
                重试
              </button>
            </div>
          ) : health ? (
            <div className="space-y-4 text-small text-text-secondary">
              <p>应用：{health.app_name}</p>
              <p>环境：{health.environment}</p>
              <p className="inline-flex items-center gap-6 text-success">
                <span className="inline-block w-8 h-8 rounded-full bg-success" aria-hidden="true" />
                {health.status === "ok" ? "运行正常" : health.status}
              </p>
            </div>
          ) : (
            <p className="text-small text-text-secondary animate-pulse">加载中…</p>
          )}
        </section>

        {/* 开发身份 */}
        <section className="rounded-card border border-border bg-surface p-20 space-y-12">
          <h2 className="text-h2 text-text-primary flex items-center gap-8">
            <ShieldCheck size={18} className="text-brand" />
            开发身份
          </h2>
          <p className="text-small text-text-secondary">
            当前处于开发环境，使用 <code className="rounded-input bg-surface-subtle px-8 py-2 text-brand">X-User-ID</code>{" "}
            传递临时用户身份。生产环境会替换为可信认证（JWT/OAuth），不再信任客户端提供的用户 ID。
          </p>
        </section>

        {/* 数据与隐私 */}
        <section className="rounded-card border border-border bg-surface p-20 space-y-12">
          <h2 className="text-h2 text-text-primary flex items-center gap-8">
            <Trash2 size={18} className="text-danger" />
            数据与隐私
          </h2>
          <p className="text-small text-text-secondary">
            清除个人档案会删除你的风格偏好、偏好来源与待确认候选，衣橱与已保存穿搭不受影响。
          </p>
          <button
            type="button"
            onClick={() => setConfirmOpen(true)}
            className="inline-flex items-center gap-8 px-16 py-8 rounded-input border border-danger/40 text-danger
                       hover:bg-danger/5 transition-colors text-small"
          >
            <Trash2 size={16} />
            清除个人档案
          </button>
        </section>
      </div>

      {confirmOpen && (
        <ConfirmDialog
          title="清除个人档案？"
          description="将删除风格偏好、偏好来源和待确认候选。此操作无法撤销。"
          confirmLabel="清除档案"
          busy={deleteProfileMutation.isPending}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={handleClearProfile}
        />
      )}
    </div>
  );
}

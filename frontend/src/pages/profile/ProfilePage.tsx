import ProfileEditor from "@/features/style-profile/ProfileEditor";
import CandidatesList from "@/features/style-profile/CandidatesList";
import MemoriesList from "@/features/style-profile/MemoriesList";

export default function ProfilePage() {
  return (
    <div className="flex-1 overflow-y-auto px-16 py-32 md:px-32">
      <div className="max-w-content mx-auto space-y-32">
        {/* 页面标题 */}
        <div>
          <p className="mb-8 text-caption font-medium uppercase tracking-[0.18em] text-brand">My style / 04</p>
          <h1 className="text-h1 text-text-primary">风格档案</h1>
          <p className="text-small text-text-secondary mt-8">
            这里保存你明确确认的长期偏好。系统不会自动修改你的档案。
          </p>
        </div>

        {/* 明确偏好 */}
        <ProfileEditor />

        {/* 待确认候选 */}
        <CandidatesList />

        {/* 偏好来源 */}
        <MemoriesList />
      </div>
    </div>
  );
}

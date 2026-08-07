import type { components } from "@/api/generated/schema";
import { AlertTriangle, XCircle } from "lucide-react";

type Issue = components["schemas"]["OutfitFeasibilityIssue"];

type Props = { issues: Issue[] };

export default function OutfitIssueList({ issues }: Props) {
  const errors = issues.filter((i) => i.severity === "error");
  const warnings = issues.filter((i) => i.severity === "warning");

  return (
    <div className="space-y-8">
      {errors.map((issue, i) => (
        <div
          key={`e-${i}`}
          className="flex items-start gap-10 rounded-card border border-danger/30 bg-danger/[0.06] px-14 py-10"
          role="alert"
        >
          <XCircle size={18} className="text-danger shrink-0 mt-2" aria-hidden="true" />
          <div>
            <span className="text-small font-medium text-danger">无法执行</span>
            <p className="text-small text-text-primary mt-2">{issue.message}</p>
          </div>
        </div>
      ))}
      {warnings.map((issue, i) => (
        <div
          key={`w-${i}`}
          className="flex items-start gap-10 rounded-card border border-warning/30 bg-warning/[0.06] px-14 py-10"
          role="alert"
        >
          <AlertTriangle size={18} className="text-warning shrink-0 mt-2" aria-hidden="true" />
          <div>
            <span className="text-small font-medium text-warning">需要注意</span>
            <p className="text-small text-text-primary mt-2">{issue.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

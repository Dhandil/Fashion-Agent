import { BookOpen } from "lucide-react";

type Props = { sources: string[] };

export default function KnowledgeSources({ sources }: Props) {
  return (
    <details className="group">
      <summary className="inline-flex items-center gap-8 text-small text-info cursor-pointer hover:underline">
        <BookOpen size={16} aria-hidden="true" />
        知识依据 · {sources.length} 个来源
      </summary>
      <ul className="mt-8 space-y-4 pl-24" role="list">
        {sources.map((source, i) => (
          <li key={i} className="text-caption text-text-secondary break-all">
            {source}
          </li>
        ))}
      </ul>
    </details>
  );
}

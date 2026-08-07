import type { ChatMessage } from "@/stores/chat";
import OutfitCard from "@/features/outfit/OutfitCard";
import OutfitGapCard from "@/features/outfit/OutfitGapCard";
import OutfitIssueList from "@/features/outfit/OutfitIssueList";
import KnowledgeSources from "@/features/outfit/KnowledgeSources";

type Props = {
  message: ChatMessage;
  onSaveOutfit: () => void;
  savingOutfit: boolean;
};

export default function AgentMessage({ message, onSaveOutfit, savingOutfit }: Props) {
  const hasStructured =
    message.outfit || message.outfitGap || (message.outfitIssues && message.outfitIssues.length > 0);

  return (
    <div className="space-y-16">
      {/* 正文 */}
      {message.text && (
        <div className="text-body text-text-primary whitespace-pre-wrap break-words leading-relaxed">
          {message.text}
        </div>
      )}

      {/* 结构化 Outfit */}
      {message.outfit && (
        <OutfitCard
          outfit={message.outfit}
          onSave={onSaveOutfit}
          saving={savingOutfit}
        />
      )}

      {/* 衣橱缺口 */}
      {message.outfitGap && !message.outfit && (
        <OutfitGapCard gap={message.outfitGap} />
      )}

      {/* 可执行性问题 */}
      {message.outfitIssues && message.outfitIssues.length > 0 && !message.outfit && (
        <OutfitIssueList issues={message.outfitIssues} />
      )}

      {/* 知识来源 */}
      {message.sources && message.sources.length > 0 && (
        <KnowledgeSources sources={message.sources} />
      )}

      {/* 混合情景:有 Outfit 但也有 Issues */}
      {message.outfit && message.outfitIssues && message.outfitIssues.length > 0 && (
        <OutfitIssueList issues={message.outfitIssues} />
      )}

      {hasStructured && <hr className="border-border mt-8" />}
    </div>
  );
}

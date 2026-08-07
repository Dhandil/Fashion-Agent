import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentMessage from "./AgentMessage";
import type { ChatMessage } from "@/stores/chat";

function makeAgentMessage(partial: Partial<ChatMessage>): ChatMessage {
  return {
    id: "msg-1",
    role: "agent",
    text: "这是建议正文",
    createdAt: 1,
    ...partial,
  };
}

describe("AgentMessage", () => {
  it("渲染正文与结构化 Outfit 卡片", () => {
    const outfit = {
      name: "清爽简约通勤穿搭",
      scenario: "通勤",
      season: "夏季",
      style_tags: ["简约", "通勤"],
      items: [
        {
          role: "上装",
          name: "浅蓝色亚麻衬衫",
          source: "wardrobe" as const,
          source_reference_id: "shirt-001",
        },
      ],
      recommendation_reason: "使用已有衣物完成搭配。",
      alternatives: [],
      wardrobe_gaps: [],
      notes: null,
    };

    render(
      <AgentMessage
        message={makeAgentMessage({ outfit })}
        onSaveOutfit={vi.fn()}
        savingOutfit={false}
      />,
    );

    expect(screen.getByText("这是建议正文")).toBeInTheDocument();
    expect(screen.getByText("清爽简约通勤穿搭")).toBeInTheDocument();
    expect(screen.getByText("浅蓝色亚麻衬衫")).toBeInTheDocument();
    expect(screen.getByText("我的衣橱")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /保存这套穿搭/ })).toBeInTheDocument();
  });

  it("有缺口时渲染衣橱缺口卡片", () => {
    const gap = {
      missing_roles: ["鞋履"],
      gaps: [
        { role: "鞋履", suggested_item: "黑色乐福鞋", reason: "衣橱缺少适合通勤的鞋" },
      ],
      reason: "鞋履为通勤穿搭的核心单品。",
      shopping_search_allowed: true,
      next_actions: ["search_products", "add_wardrobe_items"],
    } as unknown as Parameters<typeof AgentMessage>[0]["message"]["outfitGap"];

    render(
      <AgentMessage
        message={makeAgentMessage({ outfitGap: gap })}
        onSaveOutfit={vi.fn()}
        savingOutfit={false}
      />,
    );

    expect(screen.getByText(/还缺少 1 个核心单品/)).toBeInTheDocument();
    expect(screen.getByText(/衣橱缺少适合通勤的鞋/)).toBeInTheDocument();
    // 允许购物时显示可点击的搜索商品按钮
    expect(screen.getByRole("button", { name: /搜索商品/ })).toBeInTheDocument();
  });

  it("有风险时渲染提示列表", () => {
    const issues = [
      {
        code: "missing_core_role",
        severity: "error",
        message: "缺少上装",
      },
      {
        code: "hot_weather_conflict",
        severity: "warning",
        message: "降温建议加外套",
      },
    ] as Parameters<typeof AgentMessage>[0]["message"]["outfitIssues"];

    render(
      <AgentMessage
        message={makeAgentMessage({ outfitIssues: issues })}
        onSaveOutfit={vi.fn()}
        savingOutfit={false}
      />,
    );

    expect(screen.getByText("无法执行")).toBeInTheDocument();
    expect(screen.getByText("缺少上装")).toBeInTheDocument();
    expect(screen.getByText("需要注意")).toBeInTheDocument();
    expect(screen.getByText("降温建议加外套")).toBeInTheDocument();
  });

  it("有来源时渲染知识依据折叠区", () => {
    render(
      <AgentMessage
        message={makeAgentMessage({ sources: ["knowledge/01_materials/fibers/linen.md"] })}
        onSaveOutfit={vi.fn()}
        savingOutfit={false}
      />,
    );

    expect(screen.getByText(/知识依据/)).toBeInTheDocument();
  });
});

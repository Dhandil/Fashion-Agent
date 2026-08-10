import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { setUserId } from "@/api/client";
import type { components } from "@/api/generated/schema";
import WardrobeCard from "./WardrobeCard";

setUserId("test-user");

const item: components["schemas"]["WardrobeItemResponse"] = {
  wardrobe_item_id: "shirt-001",
  name: "浅蓝色衬衫",
  category: "衬衫",
  brand: null,
  colors: ["浅蓝色"],
  materials: ["亚麻"],
  size: "M",
  style_tags: [],
  seasons: [],
  scenarios: [],
  image_url: "/api/v1/wardrobe/images/asset-001/content",
  image_asset_id: "asset-001",
  status: "available",
  notes: null,
};

describe("WardrobeCard private image", () => {
  it("loads private image with identity header and releases object URL", async () => {
    const blob = new Blob(["image"], { type: "image/jpeg" });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(blob),
    });
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:wardrobe-image");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(
      <WardrobeCard
        item={item}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onToggleStatus={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("img", { name: "浅蓝色衬衫" })).toHaveAttribute(
        "src",
        "blob:wardrobe-image",
      );
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/wardrobe/images/asset-001/content",
      expect.objectContaining({
        headers: expect.objectContaining({ "X-User-ID": "test-user" }),
      }),
    );

    unmount();
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:wardrobe-image");

    vi.unstubAllGlobals();
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });
});

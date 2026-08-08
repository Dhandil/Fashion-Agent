import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ProductSearchDrawer from "./ProductSearchDrawer";
import { useProductSearch } from "@/features/outfit/api";

vi.mock("@/features/outfit/api", () => ({
  useProductSearch: vi.fn(),
}));

describe("ProductSearchDrawer", () => {
  beforeEach(() => {
    vi.mocked(useProductSearch).mockReturnValue({
      data: { items: [], count: 0, total: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useProductSearch>);
  });

  it("在开关抽屉时保持 Hook 数量稳定", () => {
    const view = render(
      <ProductSearchDrawer
        open={false}
        gapRole="鞋履"
        onClose={vi.fn()}
      />,
    );

    view.rerender(
      <ProductSearchDrawer
        open
        gapRole="鞋履"
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "搜索商品" })).toBeInTheDocument();
    expect(useProductSearch).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "鞋履" }),
      true,
    );
  });
});

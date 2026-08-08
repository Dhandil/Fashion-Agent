import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WardrobeFormDrawer from "./WardrobeFormDrawer";
import { setUserId } from "@/api/client";

setUserId("test-user");

describe("WardrobeFormDrawer", () => {
  it("空表单提交时显示名称与品类必填错误", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <WardrobeFormDrawer
        open
        mode="create"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /加入衣橱/ }));

    await waitFor(() => {
      expect(screen.getByText("请输入衣物名称")).toBeInTheDocument();
      expect(screen.getByText("请输入品类")).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("填写名称与品类后提交成功", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <WardrobeFormDrawer
        open
        mode="create"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await userEvent.type(screen.getByLabelText("名称 *"), "浅蓝色亚麻衬衫");
    await userEvent.type(screen.getByLabelText("品类 *"), "衬衫");
    await userEvent.click(screen.getByRole("button", { name: /加入衣橱/ }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    const values = onSubmit.mock.calls[0]![0];
    expect(values.name).toBe("浅蓝色亚麻衬衫");
    expect(values.category).toBe("衬衫");
    expect(values.status).toBe("available");
  });

  it("可以输入并提交自定义颜色标签", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <WardrobeFormDrawer
        open
        mode="create"
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await userEvent.type(screen.getByPlaceholderText("输入颜色后回车"), "雾霾蓝");
    await userEvent.keyboard("{Enter}");

    expect(screen.getByRole("button", { name: "移除 雾霾蓝" })).toBeInTheDocument();
  });

  it("编辑模式预填已有衣物信息", () => {
    render(
      <WardrobeFormDrawer
        open
        mode="edit"
        item={{
          wardrobe_item_id: "shirt-001",
          name: "深灰色直筒西裤",
          category: "长裤",
          brand: null,
          colors: ["深灰色"],
          materials: [],
          size: "M",
          style_tags: ["简约"],
          seasons: [],
          scenarios: [],
          image_url: null,
          status: "available",
          notes: null,
        }}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("名称 *")).toHaveValue("深灰色直筒西裤");
    expect(screen.getByLabelText("品类 *")).toHaveValue("长裤");
    expect(screen.getByLabelText("尺码（可选）")).toHaveValue("M");
  });
});

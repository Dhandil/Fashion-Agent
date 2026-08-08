import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PromptComposer from "./PromptComposer";

describe("PromptComposer", () => {
  it("地点和日期齐全但没有事实时，提交实时天气查询信息", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "添加天气信息" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-09");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "通勤怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).toHaveBeenCalledWith(
      "通勤怎么穿",
      undefined,
      { location: "上海", target_date: "2026-08-09" },
    );
  });

  it("填写天气事实时，提交手动天气上下文", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "添加天气信息" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-09");
    await user.type(screen.getByRole("textbox", { name: "天气状况" }), "晴");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "约会怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).toHaveBeenCalledWith(
      "约会怎么穿",
      {
        location: "上海",
        target_date: "2026-08-09",
        condition: "晴",
      },
      undefined,
    );
  });

  it("天气信息缺少日期时阻止发送并提示错误", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "添加天气信息" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "通勤怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("需要同时提供地点和日期");
  });
});

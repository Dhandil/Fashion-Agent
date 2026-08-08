import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WelcomeState from "./WelcomeState";

describe("WelcomeState", () => {
  it("首次会话提供自由输入框和快捷提示", () => {
    render(<WelcomeState onSend={vi.fn()} />);

    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getAllByRole("button").length).toBeGreaterThanOrEqual(3);
  });
});

describe("WelcomeState quick prompts", () => {
  it("点击快捷卡片时填充输入框而不是绕过天气字段直接发送", async () => {
    const user = userEvent.setup();
    render(<WelcomeState onSend={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "明天通勤怎么穿？" }));

    expect(screen.getByRole("textbox")).toHaveValue("明天通勤怎么穿？");
  });
});

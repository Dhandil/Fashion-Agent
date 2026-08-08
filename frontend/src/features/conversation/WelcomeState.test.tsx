import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import WelcomeState from "./WelcomeState";

describe("WelcomeState", () => {
  it("首次会话提供自由输入框和快捷提示", () => {
    render(<WelcomeState onSend={vi.fn()} />);

    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getAllByRole("button").length).toBeGreaterThanOrEqual(3);
  });
});

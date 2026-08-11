import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PromptComposer from "./PromptComposer";

const originalGeolocation = navigator.geolocation;

afterEach(() => {
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    value: originalGeolocation,
  });
});

describe("PromptComposer", () => {
  it("地点和日期齐全但没有事实时，提交实时天气查询信息", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-09");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "通勤怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).toHaveBeenCalledWith(
      "通勤怎么穿",
      undefined,
      { location: "上海", target_date: "2026-08-09" },
      true,
    );
  });

  it("填写天气事实时，提交手动天气上下文", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-09");
    await user.click(screen.getByRole("button", { name: "手动填写" }));
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
      true,
    );
  });

  it("天气信息缺少日期时阻止发送并提示错误", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "上海");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "通勤怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("需要同时提供地点和日期");
  });

  it("完成实时天气设置后显示紧凑摘要并允许移除", async () => {
    const user = userEvent.setup();
    render(<PromptComposer onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "杭州");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-10");
    await user.click(screen.getByRole("button", { name: "使用实时天气" }));

    expect(screen.getByRole("button", { name: "编辑地点和天气" })).toHaveTextContent(
      "杭州 · 8/10 · 自动查询",
    );

    await user.click(screen.getByRole("button", { name: "移除地点和天气" }));

    expect(screen.getByRole("button", { name: "加入地点和天气" })).toBeInTheDocument();
  });

  it("手动天气模式没有事实时不允许完成", async () => {
    const user = userEvent.setup();
    render(<PromptComposer onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.type(screen.getByRole("textbox", { name: "天气地点" }), "成都");
    await user.type(screen.getByLabelText("天气日期"), "2026-08-10");
    await user.click(screen.getByRole("button", { name: "手动填写" }));
    await user.click(screen.getByRole("button", { name: "使用手动天气" }));

    expect(screen.getByRole("alert")).toHaveTextContent("至少提供一项天气事实");
  });

  it("点击天气卡片外部时关闭设置浮层", async () => {
    const user = userEvent.setup();
    render(<PromptComposer onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    expect(screen.getByText("地点与天气")).toBeInTheDocument();

    await user.click(document.body);

    expect(screen.queryByText("地点与天气")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "加入地点和天气" })).toBeInTheDocument();
  });

  it("获取当前位置后提交经纬度天气查询", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({
        coords: {
          latitude: 31.2304,
          longitude: 121.4737,
          accuracy: 30,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
          toJSON: () => ({}),
        },
        timestamp: Date.now(),
        toJSON: () => ({}),
      });
    });
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });
    render(<PromptComposer onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "加入地点和天气" }));
    await user.click(screen.getByRole("button", { name: "使用当前位置" }));
    await user.type(screen.getByLabelText("天气日期"), "2026-08-11");
    await user.type(screen.getByRole("textbox", { name: "穿搭需求输入" }), "今天怎么穿");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(getCurrentPosition).toHaveBeenCalledWith(
      expect.any(Function),
      expect.any(Function),
      {
        enableHighAccuracy: false,
        timeout: 10_000,
        maximumAge: 300_000,
      },
    );
    expect(onSubmit).toHaveBeenCalledWith(
      "今天怎么穿",
      undefined,
      {
        location: "当前位置",
        target_date: "2026-08-11",
        latitude: 31.2304,
        longitude: 121.4737,
      },
      true,
    );
  });

  it("默认开启衣橱优先，并允许切换为自由灵感", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PromptComposer onSubmit={onSubmit} />);

    const wardrobeToggle = screen.getByRole("button", {
      name: "衣橱优先",
    });
    expect(wardrobeToggle).toHaveAttribute("aria-pressed", "true");

    await user.click(wardrobeToggle);
    expect(wardrobeToggle).toHaveAttribute("aria-pressed", "false");
    expect(wardrobeToggle).toHaveTextContent("自由灵感");

    await user.type(
      screen.getByRole("textbox", { name: "穿搭需求输入" }),
      "给我一套周末穿搭",
    );
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(onSubmit).toHaveBeenCalledWith(
      "给我一套周末穿搭",
      undefined,
      undefined,
      false,
    );
  });
});

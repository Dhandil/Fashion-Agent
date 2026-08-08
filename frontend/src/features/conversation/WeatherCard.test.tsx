import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import WeatherCard from "./WeatherCard";

describe("WeatherCard", () => {
  it("展示天气地点、温度和降雨概率", () => {
    render(
      <WeatherCard
        weather={{
          location: "上海",
          target_date: "2026-08-09",
          condition: "晴",
          temperature_min_c: 27,
          temperature_max_c: 34,
          feels_like_c: 36,
          precipitation_probability: 10,
          humidity_percent: 70,
          wind_speed_kph: 12,
          source: "api",
          updated_at: null,
        }}
      />,
    );

    expect(screen.getByRole("region", { name: "本轮天气" })).toBeInTheDocument();
    expect(screen.getByText("上海 · 2026-08-09")).toBeInTheDocument();
    expect(screen.getByText("27° / 34°")).toBeInTheDocument();
    expect(screen.getByText("降雨 10%")).toBeInTheDocument();
  });
});

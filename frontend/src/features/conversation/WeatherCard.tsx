import {
  CloudSun,
  Droplets,
  Thermometer,
  Umbrella,
  Wind,
} from "lucide-react";
import type { WeatherSnapshot } from "@/stores/chat";

type Props = { weather: WeatherSnapshot };

function formatTemperature(value: number | null | undefined): string | null {
  return value == null ? null : `${Math.round(value)}°`;
}

export default function WeatherCard({ weather }: Props) {
  const temperature = [
    formatTemperature(weather.temperature_min_c),
    formatTemperature(weather.temperature_max_c),
  ]
    .filter(Boolean)
    .join(" / ");

  return (
    <section
      className="rounded-card border border-info/20 bg-info/[0.06] p-16 space-y-12"
      aria-label="本轮天气"
    >
      <div className="flex items-start justify-between gap-12">
        <div className="flex items-center gap-8">
          <CloudSun size={20} className="text-info" aria-hidden="true" />
          <div>
            <h3 className="text-small font-medium text-text-primary">
              {weather.location} · {weather.target_date}
            </h3>
            <p className="text-caption text-text-secondary">
              {weather.condition ?? "天气信息"}
            </p>
          </div>
        </div>
        {temperature && (
          <span className="text-h3 text-text-primary">{temperature}</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-8 text-caption text-text-secondary md:grid-cols-4">
        {weather.feels_like_c != null && (
          <div className="flex items-center gap-6">
            <Thermometer size={14} aria-hidden="true" />
            体感 {Math.round(weather.feels_like_c)}°
          </div>
        )}
        {weather.precipitation_probability != null && (
          <div className="flex items-center gap-6">
            <Umbrella size={14} aria-hidden="true" />
            降雨 {weather.precipitation_probability}%
          </div>
        )}
        {weather.humidity_percent != null && (
          <div className="flex items-center gap-6">
            <Droplets size={14} aria-hidden="true" />
            湿度 {weather.humidity_percent}%
          </div>
        )}
        {weather.wind_speed_kph != null && (
          <div className="flex items-center gap-6">
            <Wind size={14} aria-hidden="true" />
            风速 {Math.round(weather.wind_speed_kph)} km/h
          </div>
        )}
      </div>

      <p className="text-caption text-text-secondary">
        数据来源：{weather.source === "api" ? "天气服务" : weather.source}
      </p>
    </section>
  );
}

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { CloudSun, Send } from "lucide-react";
import type { components } from "@/api/generated/schema";

type WeatherInput = components["schemas"]["WeatherContextInput"];
export type WeatherQuery = {
  location: string;
  target_date: string;
};

type Props = {
  onSubmit: (
    message: string,
    weather?: WeatherInput,
    weatherQuery?: WeatherQuery,
  ) => void;
  disabled?: boolean;
  prefillMessage?: string;
};

type WeatherDraft = {
  location: string;
  targetDate: string;
  condition: string;
  minTemperature: string;
  maxTemperature: string;
  precipitationProbability: string;
};

const EMPTY_WEATHER_DRAFT: WeatherDraft = {
  location: "",
  targetDate: "",
  condition: "",
  minTemperature: "",
  maxTemperature: "",
  precipitationProbability: "",
};

export default function PromptComposer({
  onSubmit,
  disabled = false,
  prefillMessage,
}: Props) {
  const [value, setValue] = useState("");
  const [showWeather, setShowWeather] = useState(false);
  const [weatherDraft, setWeatherDraft] = useState(EMPTY_WEATHER_DRAFT);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefillMessage !== undefined) {
      setValue(prefillMessage);
      textareaRef.current?.focus();
    }
  }, [prefillMessage]);

  // 自动调整高度
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    const draft = {
      location: weatherDraft.location.trim(),
      targetDate: weatherDraft.targetDate,
      condition: weatherDraft.condition.trim(),
      minTemperature: weatherDraft.minTemperature.trim(),
      maxTemperature: weatherDraft.maxTemperature.trim(),
      precipitationProbability: weatherDraft.precipitationProbability.trim(),
    };
    const hasWeatherDraft = Object.values(draft).some(Boolean);
    if (hasWeatherDraft && (!draft.location || !draft.targetDate)) {
      setWeatherError("填写天气信息时，需要同时提供地点和日期。\n");
      return;
    }
    if (
      draft.minTemperature &&
      draft.maxTemperature &&
      Number(draft.minTemperature) > Number(draft.maxTemperature)
    ) {
      setWeatherError("最低温度不能高于最高温度。\n");
      return;
    }

    const hasManualFact = Boolean(
      draft.condition ||
        draft.minTemperature ||
        draft.maxTemperature ||
        draft.precipitationProbability,
    );
    const weather = hasWeatherDraft && hasManualFact
      ? {
          location: draft.location,
          target_date: draft.targetDate,
          ...(draft.condition ? { condition: draft.condition } : {}),
          ...(draft.minTemperature
            ? { temperature_min_c: Number(draft.minTemperature) }
            : {}),
          ...(draft.maxTemperature
            ? { temperature_max_c: Number(draft.maxTemperature) }
            : {}),
          ...(draft.precipitationProbability
            ? { precipitation_probability: Number(draft.precipitationProbability) }
            : {}),
        }
      : undefined;
    const weatherQuery =
      hasWeatherDraft && !hasManualFact
        ? { location: draft.location, target_date: draft.targetDate }
        : undefined;

    onSubmit(trimmed, weather, weatherQuery);
    setValue("");
    setWeatherDraft(EMPTY_WEATHER_DRAFT);
    setWeatherError(null);
    setShowWeather(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="sticky bottom-0 bg-canvas pt-12 pb-24 md:pb-32">
      <div className="mb-8 flex items-center justify-between">
        <button
          type="button"
          onClick={() => {
            setShowWeather((current) => !current);
            setWeatherError(null);
          }}
          disabled={disabled}
          className="inline-flex items-center gap-6 rounded-tag border border-border px-10 py-6 text-caption text-text-secondary
                     hover:bg-surface-subtle hover:text-text-primary disabled:opacity-50 transition-colors"
          aria-expanded={showWeather}
          aria-controls="weather-input-panel"
        >
          <CloudSun size={14} aria-hidden="true" />
          {showWeather ? "收起天气信息" : "添加天气信息"}
        </button>
        {weatherDraft.location && weatherDraft.targetDate && (
          <span className="text-caption text-text-secondary">已选择天气地点</span>
        )}
      </div>

      {showWeather && (
        <div
          id="weather-input-panel"
          className="mb-8 rounded-card border border-border bg-surface p-12 space-y-10"
        >
          <p className="text-caption text-text-secondary">
            只填地点和日期时，Agent 会查询实时天气；填写温度或天气状况时，将使用你提供的事实。
          </p>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            <label className="space-y-4">
              <span className="text-caption text-text-secondary">地点</span>
              <input
                value={weatherDraft.location}
                onChange={(event) => setWeatherDraft((draft) => ({ ...draft, location: event.target.value }))}
                placeholder="例如：上海"
                disabled={disabled}
                className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                aria-label="天气地点"
              />
            </label>
            <label className="space-y-4">
              <span className="text-caption text-text-secondary">日期</span>
              <input
                type="date"
                value={weatherDraft.targetDate}
                onChange={(event) => setWeatherDraft((draft) => ({ ...draft, targetDate: event.target.value }))}
                disabled={disabled}
                className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                aria-label="天气日期"
              />
            </label>
            <label className="space-y-4">
              <span className="text-caption text-text-secondary">天气状况（可选）</span>
              <input
                value={weatherDraft.condition}
                onChange={(event) => setWeatherDraft((draft) => ({ ...draft, condition: event.target.value }))}
                placeholder="例如：晴、阵雨"
                disabled={disabled}
                className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                aria-label="天气状况"
              />
            </label>
            <label className="space-y-4">
              <span className="text-caption text-text-secondary">降雨概率（%）</span>
              <input
                type="number"
                min="0"
                max="100"
                value={weatherDraft.precipitationProbability}
                onChange={(event) => setWeatherDraft((draft) => ({ ...draft, precipitationProbability: event.target.value }))}
                placeholder="例如：30"
                disabled={disabled}
                className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                aria-label="降雨概率"
              />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-8">
            <input
              type="number"
              value={weatherDraft.minTemperature}
              onChange={(event) => setWeatherDraft((draft) => ({ ...draft, minTemperature: event.target.value }))}
              placeholder="最低温度 °C"
              disabled={disabled}
              className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
              aria-label="最低温度"
            />
            <input
              type="number"
              value={weatherDraft.maxTemperature}
              onChange={(event) => setWeatherDraft((draft) => ({ ...draft, maxTemperature: event.target.value }))}
              placeholder="最高温度 °C"
              disabled={disabled}
              className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
              aria-label="最高温度"
            />
          </div>
          {weatherError && (
            <p className="text-caption text-danger" role="alert">
              {weatherError}
            </p>
          )}
        </div>
      )}
      <div className="flex items-end gap-12 rounded-card border border-border bg-surface p-12 shadow-sm">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的穿搭需求…"
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-body text-text-primary placeholder:text-text-secondary
                     outline-none py-4 px-4 max-h-[160px]"
          aria-label="穿搭需求输入"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex items-center justify-center w-40 h-40 rounded-input bg-brand text-surface
                     hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors shrink-0 touch-target"
          aria-label="发送"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="text-caption text-text-secondary mt-8 px-4">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  );
}

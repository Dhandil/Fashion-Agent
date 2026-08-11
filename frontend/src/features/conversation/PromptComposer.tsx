import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import {
  CalendarDays,
  CloudSun,
  LocateFixed,
  LoaderCircle,
  MapPin,
  Pencil,
  Send,
  Shirt,
  X,
} from "lucide-react";
import type { components } from "@/api/generated/schema";

type WeatherInput = components["schemas"]["WeatherContextInput"];
export type WeatherQuery = {
  location: string;
  target_date: string;
  latitude?: number;
  longitude?: number;
};

type Props = {
  onSubmit: (
    message: string,
    weather?: WeatherInput,
    weatherQuery?: WeatherQuery,
    wardrobePreferred?: boolean,
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
  latitude: number | null;
  longitude: number | null;
};

const EMPTY_WEATHER_DRAFT: WeatherDraft = {
  location: "",
  targetDate: "",
  condition: "",
  minTemperature: "",
  maxTemperature: "",
  precipitationProbability: "",
  latitude: null,
  longitude: null,
};

type WeatherMode = "auto" | "manual";

function formatDateInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, days: number): Date {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + days);
  return nextDate;
}

function getWeekendDate(date: Date): Date {
  const dayOfWeek = date.getDay();
  const daysUntilSaturday = dayOfWeek === 6 ? 0 : dayOfWeek === 0 ? 6 : 6 - dayOfWeek;
  return addDays(date, daysUntilSaturday);
}

function formatWeatherDate(value: string): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function hasManualWeatherFacts(draft: WeatherDraft): boolean {
  return Boolean(
    draft.condition.trim() ||
      draft.minTemperature.trim() ||
      draft.maxTemperature.trim() ||
      draft.precipitationProbability.trim(),
  );
}

export default function PromptComposer({
  onSubmit,
  disabled = false,
  prefillMessage,
}: Props) {
  const [value, setValue] = useState("");
  const [showWeather, setShowWeather] = useState(false);
  const [weatherMode, setWeatherMode] = useState<WeatherMode>("auto");
  const [weatherDraft, setWeatherDraft] = useState(EMPTY_WEATHER_DRAFT);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [wardrobePreferred, setWardrobePreferred] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const weatherPanelRef = useRef<HTMLDivElement>(null);
  const weatherTriggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (prefillMessage !== undefined) {
      setValue(prefillMessage);
      textareaRef.current?.focus();
    }
  }, [prefillMessage]);

  // 天气设置属于浮层：点击卡片和开关按钮以外的任意区域都应关闭。
  useEffect(() => {
    if (!showWeather) return;

    const handleOutsidePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (weatherPanelRef.current?.contains(target)) return;
      if (weatherTriggerRef.current?.contains(target)) return;
      setShowWeather(false);
    };

    document.addEventListener("pointerdown", handleOutsidePointerDown);
    return () => document.removeEventListener("pointerdown", handleOutsidePointerDown);
  }, [showWeather]);

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
      setShowWeather(true);
      return;
    }
    if (
      draft.minTemperature &&
      draft.maxTemperature &&
      Number(draft.minTemperature) > Number(draft.maxTemperature)
    ) {
      setWeatherError("最低温度不能高于最高温度。\n");
      setShowWeather(true);
      return;
    }

    const hasManualFact = weatherMode === "manual" && hasManualWeatherFacts(weatherDraft);
    if (weatherMode === "manual" && hasWeatherDraft && !hasManualFact) {
      setWeatherError("手动填写天气时，请至少提供一项天气事实。");
      setShowWeather(true);
      return;
    }
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
        ? {
            location: draft.location,
            target_date: draft.targetDate,
            ...(weatherDraft.latitude !== null && weatherDraft.longitude !== null
              ? {
                  latitude: weatherDraft.latitude,
                  longitude: weatherDraft.longitude,
                }
              : {}),
          }
        : undefined;

    onSubmit(trimmed, weather, weatherQuery, wardrobePreferred);
    setValue("");
    setWeatherDraft(EMPTY_WEATHER_DRAFT);
    setWeatherMode("auto");
    setWeatherError(null);
    setShowWeather(false);
  };

  const clearWeather = () => {
    setWeatherDraft(EMPTY_WEATHER_DRAFT);
    setWeatherMode("auto");
    setWeatherError(null);
    setShowWeather(false);
  };

  const useCurrentLocation = () => {
    setWeatherError(null);
    if (!("geolocation" in navigator)) {
      setWeatherError("当前浏览器不支持定位，请手动填写地点。");
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setWeatherDraft((draft) => ({
          ...draft,
          location: "当前位置",
          latitude: Number(coords.latitude.toFixed(6)),
          longitude: Number(coords.longitude.toFixed(6)),
        }));
        setWeatherError(null);
        setIsLocating(false);
      },
      (error) => {
        const message = error.code === error.PERMISSION_DENIED
          ? "定位权限未开启，请允许访问位置或手动填写地点。"
          : "暂时无法获取当前位置，请稍后重试或手动填写地点。";
        setWeatherError(message);
        setIsLocating(false);
      },
      {
        enableHighAccuracy: false,
        timeout: 10_000,
        maximumAge: 300_000,
      },
    );
  };

  const finishWeather = () => {
    if (!weatherDraft.location.trim() || !weatherDraft.targetDate) {
      setWeatherError("请选择地点和日期后再完成。");
      return;
    }
    if (weatherMode === "manual" && !hasManualWeatherFacts(weatherDraft)) {
      setWeatherError("手动填写天气时，请至少提供一项天气事实。");
      return;
    }
    setWeatherError(null);
    setShowWeather(false);
  };

  const selectWeatherMode = (mode: WeatherMode) => {
    setWeatherMode(mode);
    setWeatherError(null);
    if (mode === "auto") {
      setWeatherDraft((draft) => ({
        ...draft,
        condition: "",
        minTemperature: "",
        maxTemperature: "",
        precipitationProbability: "",
      }));
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const today = new Date();
  const dateShortcuts = [
    { label: "今天", value: formatDateInput(today) },
    { label: "明天", value: formatDateInput(addDays(today, 1)) },
    { label: "周末", value: formatDateInput(getWeekendDate(today)) },
  ];
  const hasWeatherSelection = Boolean(
    weatherDraft.location.trim() && weatherDraft.targetDate,
  );

  return (
    <div className="relative z-20 shrink-0 bg-canvas/95 pb-24 pt-12 md:pb-32">
      <div className="mb-8 flex min-h-[2rem] flex-wrap items-center gap-8">
        <button
          type="button"
          onClick={() => setWardrobePreferred((current) => !current)}
          disabled={disabled}
          aria-label="衣橱优先"
          aria-pressed={wardrobePreferred}
          title="开启后，穿搭请求会先查询你当前可用的衣物"
          className={`inline-flex items-center gap-6 rounded-tag border px-10 py-6 text-caption font-medium transition-colors disabled:opacity-50 ${
            wardrobePreferred
              ? "border-brand/25 bg-brand/[0.09] text-brand"
              : "border-border text-text-secondary hover:bg-surface-subtle hover:text-text-primary"
          }`}
        >
          <Shirt size={14} aria-hidden="true" />
          {wardrobePreferred ? "衣橱优先" : "自由灵感"}
        </button>

        {hasWeatherSelection && !showWeather ? (
          <div className="inline-flex max-w-full items-center rounded-tag border border-brand/20 bg-brand/[0.06] text-caption text-brand">
            <button
              ref={weatherTriggerRef}
              type="button"
              onClick={() => setShowWeather(true)}
              disabled={disabled}
              className="inline-flex min-w-0 items-center gap-6 px-10 py-6 disabled:opacity-50"
              aria-label="编辑地点和天气"
            >
              <CloudSun size={14} className="shrink-0" aria-hidden="true" />
              <span className="truncate">
                {weatherDraft.location.trim()} · {formatWeatherDate(weatherDraft.targetDate)} · {weatherMode === "auto" ? "自动查询" : "手动天气"}
              </span>
              <Pencil size={12} className="shrink-0" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={clearWeather}
              disabled={disabled}
              className="flex h-32 w-32 shrink-0 items-center justify-center border-l border-brand/15 hover:bg-brand/10 disabled:opacity-50"
              aria-label="移除地点和天气"
            >
              <X size={13} aria-hidden="true" />
            </button>
          </div>
        ) : (
          <button
            ref={weatherTriggerRef}
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
            {showWeather ? "收起地点和天气" : "加入地点和天气"}
          </button>
        )}
      </div>

      {showWeather && (
        <>
          <div
            className="fixed inset-0 z-30 bg-text-primary/20 backdrop-blur-[1px] md:bg-transparent md:backdrop-blur-none"
            data-testid="weather-backdrop"
            aria-hidden="true"
          />
          <div
            ref={weatherPanelRef}
            id="weather-input-panel"
            className="fixed inset-x-12 bottom-[5.25rem] z-40 max-h-[72dvh] space-y-12 overflow-y-auto rounded-card-lg border border-brand/15 bg-surface p-16 shadow-[0_18px_48px_rgba(37,40,58,0.20)] md:absolute md:bottom-full md:left-1/2 md:right-auto md:mb-0 md:max-h-[70dvh] md:w-[42rem] md:max-w-[calc(100%-4rem)] md:-translate-x-1/2 md:shadow-[0_14px_36px_rgba(50,57,115,0.14)]"
          >
          <div className="flex items-start justify-between gap-12 border-b border-dashed border-border pb-12">
            <div>
              <p className="text-small font-semibold text-text-primary">地点与天气</p>
              <p className="mt-2 text-caption text-text-secondary">选择地点和日期，Agent 会在回答前查询对应天气。</p>
            </div>
            <button
              type="button"
              onClick={() => setShowWeather(false)}
              className="flex h-32 w-32 shrink-0 items-center justify-center rounded-card text-text-secondary hover:bg-surface-subtle"
              aria-label="关闭天气设置"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="inline-flex rounded-card bg-surface-subtle p-4" aria-label="天气信息来源">
            <button
              type="button"
              onClick={() => selectWeatherMode("auto")}
              aria-pressed={weatherMode === "auto"}
              className={`rounded-input px-12 py-6 text-caption font-medium transition-all ${weatherMode === "auto" ? "bg-surface text-brand shadow-sm" : "text-text-secondary"}`}
            >
              自动查询
            </button>
            <button
              type="button"
              onClick={() => selectWeatherMode("manual")}
              aria-pressed={weatherMode === "manual"}
              className={`rounded-input px-12 py-6 text-caption font-medium transition-all ${weatherMode === "manual" ? "bg-surface text-brand shadow-sm" : "text-text-secondary"}`}
            >
              手动填写
            </button>
          </div>

          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            <div className="space-y-4">
              <span className="flex items-center justify-between gap-8 text-caption text-text-secondary">
                <span className="inline-flex items-center gap-4"><MapPin size={12} aria-hidden="true" />地点</span>
                <button
                  type="button"
                  onClick={useCurrentLocation}
                  disabled={disabled || isLocating}
                  className="inline-flex items-center gap-4 rounded-tag px-6 py-2 text-brand hover:bg-brand/[0.07] disabled:opacity-50"
                  aria-label="使用当前位置"
                >
                  {isLocating ? <LoaderCircle size={12} className="animate-spin" aria-hidden="true" /> : <LocateFixed size={12} aria-hidden="true" />}
                  {isLocating ? "定位中…" : weatherDraft.latitude !== null ? "已定位" : "使用当前位置"}
                </button>
              </span>
              <div className="relative">
                <input
                  value={weatherDraft.location}
                  onChange={(event) => setWeatherDraft((draft) => ({
                    ...draft,
                    location: event.target.value,
                    latitude: null,
                    longitude: null,
                  }))}
                  placeholder="例如：上海"
                  disabled={disabled}
                  className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                  aria-label="天气地点"
                />
              </div>
            </div>
            <label className="space-y-4">
              <span className="inline-flex items-center gap-4 text-caption text-text-secondary"><CalendarDays size={12} aria-hidden="true" />日期</span>
              <input
                type="date"
                value={weatherDraft.targetDate}
                onChange={(event) => setWeatherDraft((draft) => ({ ...draft, targetDate: event.target.value }))}
                disabled={disabled}
                className="w-full rounded-input border border-border bg-canvas px-10 py-8 text-small outline-none focus:border-brand"
                aria-label="天气日期"
              />
            </label>
          </div>

          <div className="flex flex-wrap gap-6" aria-label="快捷日期">
            {dateShortcuts.map((shortcut) => (
              <button
                key={shortcut.label}
                type="button"
                onClick={() => setWeatherDraft((draft) => ({ ...draft, targetDate: shortcut.value }))}
                aria-pressed={weatherDraft.targetDate === shortcut.value}
                className={`rounded-tag border px-10 py-4 text-caption transition-colors ${weatherDraft.targetDate === shortcut.value ? "border-brand bg-brand text-surface" : "border-border text-text-secondary hover:border-brand/30 hover:text-brand"}`}
              >
                {shortcut.label}
              </button>
            ))}
          </div>

          {weatherMode === "manual" && (
            <div className="space-y-8 rounded-card border border-dashed border-border bg-canvas/70 p-12">
              <p className="text-caption text-text-secondary">没有网络或你掌握更准确的信息时，可手动提供天气事实。</p>
              <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
                <label className="space-y-4">
                  <span className="text-caption text-text-secondary">天气状况</span>
                  <input
                    value={weatherDraft.condition}
                    onChange={(event) => setWeatherDraft((draft) => ({ ...draft, condition: event.target.value }))}
                    placeholder="例如：晴、阵雨"
                    disabled={disabled}
                    className="w-full rounded-input border border-border bg-surface px-10 py-8 text-small outline-none focus:border-brand"
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
                    className="w-full rounded-input border border-border bg-surface px-10 py-8 text-small outline-none focus:border-brand"
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
                  className="w-full rounded-input border border-border bg-surface px-10 py-8 text-small outline-none focus:border-brand"
                  aria-label="最低温度"
                />
                <input
                  type="number"
                  value={weatherDraft.maxTemperature}
                  onChange={(event) => setWeatherDraft((draft) => ({ ...draft, maxTemperature: event.target.value }))}
                  placeholder="最高温度 °C"
                  disabled={disabled}
                  className="w-full rounded-input border border-border bg-surface px-10 py-8 text-small outline-none focus:border-brand"
                  aria-label="最高温度"
                />
              </div>
            </div>
          )}

          {weatherError && (
            <p className="text-caption text-danger" role="alert">
              {weatherError}
            </p>
          )}
          <div className="flex items-center justify-between gap-8 border-t border-border/70 pt-12">
            <button
              type="button"
              onClick={clearWeather}
              className="px-10 py-6 text-caption text-text-secondary hover:text-danger"
            >
              清除
            </button>
            <button
              type="button"
              onClick={finishWeather}
              className="rounded-input bg-brand px-14 py-8 text-small font-medium text-surface hover:bg-brand-hover"
            >
              {weatherMode === "auto" ? "使用实时天气" : "使用手动天气"}
            </button>
          </div>
          </div>
        </>
      )}
      <div className="flex items-end gap-12 rounded-card-lg border border-border/80 bg-surface p-12 shadow-[0_12px_32px_rgba(37,40,58,0.08)] transition-shadow focus-within:border-brand/40 focus-within:shadow-[0_14px_36px_rgba(72,86,200,0.16)]">
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
          className="flex items-center justify-center h-44 w-44 rounded-card bg-brand text-surface
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

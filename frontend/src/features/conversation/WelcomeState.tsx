import { useState, type ComponentProps } from "react";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarHeart,
  CloudSun,
  Footprints,
  Shirt,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import PromptComposer from "@/features/conversation/PromptComposer";

type Props = {
  onSend: ComponentProps<typeof PromptComposer>["onSubmit"];
};

type QuickPrompt = {
  label: string;
  prompt: string;
  icon: LucideIcon;
};

const QUICK_PROMPTS: QuickPrompt[] = [
  { label: "通勤", prompt: "明天通勤怎么穿？", icon: BriefcaseBusiness },
  { label: "约会", prompt: "周末约会搭一套", icon: CalendarHeart },
  { label: "随心搭", prompt: "从衣橱帮我搭配", icon: Sparkles },
];

export default function WelcomeState({ onSend }: Props) {
  const [prefillMessage, setPrefillMessage] = useState<string>();
  const todayLabel = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date());

  return (
    <div className="flex min-h-0 flex-1 flex-col px-16 md:px-32">
      <div className="page-frame flex flex-1 items-center justify-center py-24 md:py-40">
        <div className="grid w-full max-w-[74rem] items-center gap-32 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="text-center lg:text-left" aria-labelledby="welcome-title">
            <div className="mb-16 inline-flex items-center gap-8 rounded-tag border border-brand/20 bg-surface px-12 py-6 text-caption font-medium tracking-wide text-brand shadow-sm">
              <span className="h-8 w-8 rotate-12 rounded-sm bg-accent" aria-hidden="true" />
              MY CLOSET · TODAY
            </div>

            <div className="space-y-12">
              <h1
                id="welcome-title"
                className="text-display font-semibold tracking-[-0.035em] text-text-primary md:text-[3rem] md:leading-[1.08]"
              >
                打开衣橱，
                <span className="relative whitespace-nowrap text-brand">
                  今天穿得像自己。
                  <span
                    className="absolute -bottom-4 left-0 h-4 w-full -rotate-1 rounded-tag bg-accent/40"
                    aria-hidden="true"
                  />
                </span>
              </h1>
              <p className="mx-auto max-w-xl text-body leading-7 text-text-secondary lg:mx-0">
                从你已经拥有的衣服出发，把场景、天气和当天心情，整理成真正能穿出门的一套。
              </p>
            </div>

            <div className="mt-24 grid gap-8 sm:grid-cols-3">
              {QUICK_PROMPTS.map(({ label, prompt, icon: Icon }, index) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setPrefillMessage(prompt)}
                  className="group relative overflow-hidden rounded-card border border-border bg-surface px-14 py-12 text-left shadow-sm transition-all hover:-translate-y-2 hover:border-brand/30 hover:shadow-[0_12px_28px_rgba(50,57,115,0.12)]"
                >
                  <span
                    className="absolute right-10 top-8 text-[0.62rem] font-medium tracking-[0.16em] text-text-secondary/55"
                    aria-hidden="true"
                  >
                    0{index + 1}
                  </span>
                  <Icon size={18} className="mb-12 text-brand" strokeWidth={1.8} aria-hidden="true" />
                  <span className="block text-caption font-medium tracking-wide text-accent" aria-hidden="true">
                    {label}
                  </span>
                  <span className="mt-2 block text-small font-medium text-text-primary transition-colors group-hover:text-brand">
                    {prompt}
                  </span>
                  <ArrowUpRight
                    size={14}
                    className="absolute bottom-12 right-12 translate-y-2 text-brand opacity-0 transition-all group-hover:translate-y-0 group-hover:opacity-100"
                    aria-hidden="true"
                  />
                  <span className="absolute inset-x-0 bottom-0 h-3 origin-left scale-x-0 bg-accent transition-transform group-hover:scale-x-100" aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <aside className="relative hidden lg:block" aria-label="今日衣橱画板">
            <div
              className="gentle-float absolute -left-12 -top-12 h-64 w-64 -rotate-6 rounded-card border border-accent/25 bg-accent/10"
              aria-hidden="true"
            />
            <div
              className="absolute -bottom-10 -right-10 h-48 w-48 rotate-6 rounded-card border border-brand/20 bg-brand/[0.08]"
              aria-hidden="true"
            />

            <div className="relative overflow-hidden rounded-card-lg border border-brand/15 bg-surface p-24 shadow-[0_24px_60px_rgba(50,57,115,0.14)]">
              <div className="absolute right-20 top-0 h-20 w-56 bg-accent/15" aria-hidden="true" />
              <div className="flex items-start justify-between gap-16 border-b border-dashed border-border pb-16">
                <div>
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-brand">
                    Today&apos;s closet board
                  </p>
                  <h2 className="mt-4 text-h2 font-semibold text-text-primary">今天穿哪一套？</h2>
                </div>
                <span className="rounded-tag bg-text-primary px-10 py-4 text-[0.62rem] tracking-[0.08em] text-surface">
                  {todayLabel}
                </span>
              </div>

              <div className="mt-16 grid grid-cols-[1.18fr_0.82fr] gap-10" aria-hidden="true">
                <div className="relative flex min-h-[12.5rem] flex-col items-center justify-center overflow-hidden rounded-card bg-brand/[0.08] p-16">
                  <span className="absolute left-12 top-10 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-brand/60">Upper</span>
                  <span className="absolute right-12 top-10 font-mono text-caption text-brand/35">01</span>
                  <div className="flex h-80 w-80 items-center justify-center rounded-full bg-surface shadow-sm">
                    <Shirt size={42} strokeWidth={1.25} className="text-brand" />
                  </div>
                  <p className="mt-12 text-small font-semibold text-text-primary">从一件想穿的开始</p>
                  <p className="mt-2 text-caption text-text-secondary">你的衣橱，不是随机图片</p>
                </div>
                <div className="grid gap-10">
                  <div className="relative flex flex-col justify-between rounded-card bg-accent/10 p-12">
                    <div className="flex items-start justify-between">
                      <Sparkles size={21} strokeWidth={1.6} className="text-accent" />
                      <span className="font-mono text-caption text-accent/45">02</span>
                    </div>
                    <div>
                      <p className="text-small font-semibold text-text-primary">版型与层次</p>
                      <p className="text-caption text-text-secondary">让搭配更像你</p>
                    </div>
                  </div>
                  <div className="relative flex flex-col justify-between rounded-card bg-success/10 p-12">
                    <div className="flex items-start justify-between">
                      <Footprints size={21} strokeWidth={1.6} className="text-success" />
                      <span className="font-mono text-caption text-success/45">03</span>
                    </div>
                    <div>
                      <p className="text-small font-semibold text-text-primary">走得舒服</p>
                      <p className="text-caption text-text-secondary">路程也要考虑</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-12 grid grid-cols-3 gap-6 border-t border-dashed border-border pt-12">
                <div className="rounded-card bg-canvas/80 px-8 py-8">
                  <p className="text-[0.62rem] text-text-secondary">场景</p>
                  <p className="text-caption font-medium text-text-primary">等你输入</p>
                </div>
                <div className="rounded-card bg-canvas/80 px-8 py-8">
                  <p className="flex items-center gap-4 text-[0.62rem] text-text-secondary">
                    <CloudSun size={11} aria-hidden="true" /> 天气
                  </p>
                  <p className="text-caption font-medium text-text-primary">按需查询</p>
                </div>
                <div className="rounded-card bg-canvas/80 px-8 py-8">
                  <p className="text-[0.62rem] text-text-secondary">原则</p>
                  <p className="text-caption font-medium text-brand">衣橱优先</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      <div className="page-frame mx-auto w-full max-w-chat">
        <PromptComposer onSubmit={onSend} prefillMessage={prefillMessage} />
      </div>
    </div>
  );
}

import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      // ── 品牌色板 · 来自 visual-direction §7 ──
      canvas: "#F6F3EE",
      surface: "#FFFFFF",
      "surface-subtle": "#ECE8E1",
      "text-primary": "#202522",
      "text-secondary": "#626A65",
      border: "#D8D3CB",
      brand: "#315E52",
      "brand-hover": "#264B42",
      accent: "#A85D3B",
      success: "#287552",
      warning: "#8A6200",
      danger: "#A43C3C",
      info: "#366A8A",
    },
    fontFamily: {
      sans: [
        "Inter",
        '"PingFang SC"',
        '"Microsoft YaHei"',
        "system-ui",
        "sans-serif",
      ],
    },
    fontSize: {
      display: ["2rem", { lineHeight: "2.5rem", fontWeight: "500" }],
      h1: ["1.75rem", { lineHeight: "2.25rem", fontWeight: "500" }],
      h2: ["1.375rem", { lineHeight: "1.875rem", fontWeight: "500" }],
      h3: ["1.125rem", { lineHeight: "1.625rem", fontWeight: "500" }],
      body: ["1rem", { lineHeight: "1.625rem", fontWeight: "400" }],
      small: ["0.875rem", { lineHeight: "1.3125rem", fontWeight: "400" }],
      caption: ["0.75rem", { lineHeight: "1.125rem", fontWeight: "400" }],
    },
    borderRadius: {
      none: "0",
      input: "0.5rem",
      card: "0.75rem",
      "card-lg": "1rem",
      tag: "9999px",
      full: "9999px",
    },
    spacing: {
      0: "0",
      2: "0.125rem",
      4: "0.25rem",
      8: "0.5rem",
      12: "0.75rem",
      16: "1rem",
      20: "1.25rem",
      24: "1.5rem",
      32: "2rem",
      40: "2.5rem",
      48: "3rem",
      56: "3.5rem",
      64: "4rem",
      80: "5rem",
    },
    maxWidth: {
      content: "55rem",
      chat: "47.5rem",
      sidebar: "14rem",
      context: "21rem",
    },
    extend: {
      transitionDuration: {
        DEFAULT: "180ms",
      },
    },
  },
  plugins: [],
} satisfies Config;

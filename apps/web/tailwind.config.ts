import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}", "../../packages/shared/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#090d12",
        foreground: "#f7f8fb",
        muted: "#9da6b5",
        border: "rgba(255,255,255,0.10)",
        panel: "rgba(21,27,35,0.82)",
        accent: "#ff5a00",
        success: "#58d532",
      },
      boxShadow: {
        panel: "0 22px 80px rgba(0,0,0,0.32)",
        glow: "0 0 42px rgba(255,90,0,0.22)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#0c1219",
          elevated: "#141c27",
          muted: "#1c2736",
        },
        ink: {
          DEFAULT: "#e8eef6",
          muted: "#9aabc0",
          faint: "#6b7c91",
        },
        accent: {
          DEFAULT: "#2dd4bf",
          soft: "#115e59",
          strong: "#14b8a6",
        },
        line: "#243044",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 20px 50px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(45, 212, 191, 0.18), transparent 55%), radial-gradient(ellipse 60% 50% at 15% 80%, rgba(56, 120, 180, 0.15), transparent 50%)",
      },
    },
  },
  plugins: [],
};

export default config;

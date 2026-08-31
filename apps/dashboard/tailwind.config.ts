import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      colors: {
        ink: "#101311",
        paper: "#f2f0e8",
        signal: "#c8ff4d",
        ember: "#ff795c",
        mist: "#d9ddd4",
      },
      boxShadow: {
        lift: "0 18px 50px rgba(16, 19, 17, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx,js,jsx}",
    "./components/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d12",
        panel: "#151923",
        border: "#1e2533",
        accent: "#6ea8fe",
        violet: "#a78bfa",
        teal: "#2dd4bf",
        ok: "#34d399",
        bad: "#f87171",
        warn: "#fbbf24",
        muted: "#8b93a7",
        text: "#e6e9ef",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

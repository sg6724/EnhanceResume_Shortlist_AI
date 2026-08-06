/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx,js,jsx}",
    "./components/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#F5F3EF",
        panel: "#FFFFFF",
        border: "#E6E2D8",
        accent: "#3B82F6",
        violet: "#B9A6F5",
        coral: "#FF6F5E",
        teal: "#2dd4bf",
        ok: "#16A34A",
        bad: "#DC2626",
        warn: "#D97706",
        muted: "#6B6B74",
        text: "#141414",
        // shadcn/ui semantic roles, mapped onto the palette above (not shadcn's stock theme)
        background: "#F5F3EF",
        foreground: "#141414",
        card: { DEFAULT: "#FFFFFF", foreground: "#141414" },
        popover: { DEFAULT: "#FFFFFF", foreground: "#141414" },
        primary: { DEFAULT: "#111114", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#FFFFFF", foreground: "#141414" },
        destructive: { DEFAULT: "#DC2626", foreground: "#FFFFFF" },
        input: "#E6E2D8",
        ring: "#111114",
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

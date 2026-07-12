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
        // shadcn/ui semantic roles, mapped onto the palette above (not shadcn's stock theme)
        background: "#0b0d12",
        foreground: "#e6e9ef",
        card: { DEFAULT: "#151923", foreground: "#e6e9ef" },
        popover: { DEFAULT: "#151923", foreground: "#e6e9ef" },
        primary: { DEFAULT: "#6ea8fe", foreground: "#0b0d12" },
        secondary: { DEFAULT: "#1c212c", foreground: "#e6e9ef" },
        destructive: { DEFAULT: "#f87171", foreground: "#0b0d12" },
        input: "#1e2533",
        ring: "#6ea8fe",
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
